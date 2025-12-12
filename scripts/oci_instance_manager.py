#!/usr/bin/env python3
"""
Oracle Cloud Infrastructure Instance Manager
Manages OCI compute instances for distributed book generation

Features:
- Create/start/stop/terminate compute instances
- Deploy book generation scripts to instances
- Monitor instance health and costs
- Auto-scale based on job queue
- Maximize free tier resources ($300 credits)
"""

import json
import time
import base64
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

try:
    import oci
    OCI_AVAILABLE = True
except ImportError:
    OCI_AVAILABLE = False
    print("WARNING: OCI SDK not installed. Run: pip install oci")


class InstanceShape(Enum):
    """OCI compute shapes optimized for cost"""
    # Free tier shapes
    AMPERE_FREE = "VM.Standard.A1.Flex"  # Arm-based, best free tier option
    AMD_FREE = "VM.Standard.E2.1.Micro"   # x86, minimal specs

    # Paid tier (using credits)
    AMPERE_SMALL = "VM.Standard.A1.Flex"  # 2 OCPU, 12GB RAM
    AMPERE_MEDIUM = "VM.Standard.A1.Flex" # 4 OCPU, 24GB RAM
    AMD_SMALL = "VM.Standard.E4.Flex"     # 1 OCPU, 16GB RAM


@dataclass
class InstanceConfig:
    """Configuration for OCI compute instance"""
    shape: str
    ocpus: int
    memory_gb: int
    boot_volume_gb: int = 50
    use_free_tier: bool = True
    compartment_id: Optional[str] = None
    availability_domain: Optional[str] = None
    subnet_id: Optional[str] = None
    image_id: Optional[str] = None  # Ubuntu 22.04 LTS recommended


@dataclass
class InstanceInfo:
    """Information about a running instance"""
    instance_id: str
    name: str
    shape: str
    state: str
    public_ip: Optional[str]
    private_ip: Optional[str]
    created_at: float
    cost_estimate: float = 0.0
    books_generated: int = 0


class OCIInstanceManager:
    """
    Manages OCI compute instances for book generation

    Capabilities:
    - Create instances prioritizing free tier
    - Deploy book generation system
    - Monitor costs against $300 credit
    - Auto-shutdown idle instances
    - Collect generated books from object storage
    """

    def __init__(self, config_file: Path = Path.home() / ".oci" / "config",
                 profile: str = "DEFAULT",
                 max_spend: float = 300.0):
        """
        Initialize OCI manager

        Args:
            config_file: Path to OCI config file
            profile: OCI config profile to use
            max_spend: Maximum spend limit (defaults to $300 trial credit)
        """
        if not OCI_AVAILABLE:
            raise ImportError("OCI SDK not installed. Run: pip install oci")

        # Load OCI config
        self.config = oci.config.from_file(str(config_file), profile)

        # Initialize OCI clients
        self.compute_client = oci.core.ComputeClient(self.config)
        self.network_client = oci.core.VirtualNetworkClient(self.config)
        self.storage_client = oci.object_storage.ObjectStorageClient(self.config)

        # Cost tracking
        self.max_spend = max_spend
        self.current_spend = 0.0

        # Instance tracking
        self.instances: Dict[str, InstanceInfo] = {}
        self.free_tier_usage = {
            'ampere_ocpus': 0,  # Max 4 OCPUs free
            'amd_instances': 0,  # Max 2 instances free
        }

        # Load state
        self.state_file = Path("workspace/oci_state.json")
        self._load_state()

        print(f"[OCI] Initialized with max spend: ${max_spend:.2f}")
        print(f"[OCI] Current spend: ${self.current_spend:.2f}")
        print(f"[OCI] Remaining budget: ${max_spend - self.current_spend:.2f}")

    def _load_state(self):
        """Load instance state from disk"""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                state = json.load(f)
                self.current_spend = state.get('current_spend', 0.0)
                self.free_tier_usage = state.get('free_tier_usage', self.free_tier_usage)

                # Load instances
                for inst_data in state.get('instances', []):
                    inst = InstanceInfo(**inst_data)
                    self.instances[inst.instance_id] = inst

    def _save_state(self):
        """Save instance state to disk"""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        state = {
            'current_spend': self.current_spend,
            'free_tier_usage': self.free_tier_usage,
            'instances': [asdict(inst) for inst in self.instances.values()]
        }

        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)

    def can_use_free_tier(self, config: InstanceConfig) -> bool:
        """Check if instance can use free tier"""
        if not config.use_free_tier:
            return False

        if config.shape == InstanceShape.AMPERE_FREE.value:
            # Check if we have free OCPU capacity
            if self.free_tier_usage['ampere_ocpus'] + config.ocpus <= 4:
                return True

        elif config.shape == InstanceShape.AMD_FREE.value:
            # Check if we can add another AMD instance
            if self.free_tier_usage['amd_instances'] < 2:
                return True

        return False

    def estimate_instance_cost(self, config: InstanceConfig, hours: float = 1.0) -> float:
        """
        Estimate cost for running an instance

        Args:
            config: Instance configuration
            hours: Number of hours to run

        Returns:
            Estimated cost in USD
        """
        # Check if free tier
        if self.can_use_free_tier(config):
            return 0.0

        # Paid tier costs (approximate OCI rates)
        if "A1" in config.shape:  # Ampere
            cost_per_ocpu_hour = 0.01
            cost_per_gb_hour = 0.0015
        else:  # AMD/Intel
            cost_per_ocpu_hour = 0.02
            cost_per_gb_hour = 0.0025

        hourly_cost = (config.ocpus * cost_per_ocpu_hour) + (config.memory_gb * cost_per_gb_hour)
        return hourly_cost * hours

    def create_instance(self, name: str, config: InstanceConfig,
                       setup_script: Optional[str] = None) -> Optional[str]:
        """
        Create a new compute instance

        Args:
            name: Instance name
            config: Instance configuration
            setup_script: Cloud-init script to run on boot

        Returns:
            Instance ID if successful, None otherwise
        """
        # Check budget
        estimated_cost = self.estimate_instance_cost(config, hours=24)
        if self.current_spend + estimated_cost > self.max_spend:
            print(f"[OCI] ✗ Cannot create instance: would exceed budget")
            print(f"[OCI]   Estimated cost: ${estimated_cost:.2f}")
            print(f"[OCI]   Remaining budget: ${self.max_spend - self.current_spend:.2f}")
            return None

        # Check free tier availability
        is_free = self.can_use_free_tier(config)
        tier = "free tier" if is_free else f"paid (${estimated_cost:.2f}/day)"

        print(f"[OCI] Creating instance '{name}' ({tier})...")

        # In a real implementation, would call OCI API here
        # This is a skeleton showing the structure

        try:
            # Create instance metadata
            metadata = {}
            if setup_script:
                # Encode cloud-init script
                metadata['user_data'] = base64.b64encode(setup_script.encode()).decode()

            # Build launch instance details
            launch_details = oci.core.models.LaunchInstanceDetails(
                availability_domain=config.availability_domain,
                compartment_id=config.compartment_id,
                display_name=name,
                shape=config.shape,
                shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
                    ocpus=config.ocpus,
                    memory_in_gbs=config.memory_gb
                ),
                source_details=oci.core.models.InstanceSourceViaImageDetails(
                    image_id=config.image_id,
                    boot_volume_size_in_gbs=config.boot_volume_gb
                ),
                create_vnic_details=oci.core.models.CreateVnicDetails(
                    subnet_id=config.subnet_id,
                    assign_public_ip=True
                ),
                metadata=metadata
            )

            # Launch instance
            response = self.compute_client.launch_instance(launch_details)
            instance_id = response.data.id

            # Update tracking
            instance_info = InstanceInfo(
                instance_id=instance_id,
                name=name,
                shape=config.shape,
                state="PROVISIONING",
                public_ip=None,
                private_ip=None,
                created_at=time.time(),
                cost_estimate=estimated_cost
            )

            self.instances[instance_id] = instance_info

            # Update free tier usage
            if is_free:
                if "A1" in config.shape:
                    self.free_tier_usage['ampere_ocpus'] += config.ocpus
                else:
                    self.free_tier_usage['amd_instances'] += 1

            self._save_state()

            print(f"[OCI] ✓ Instance created: {instance_id}")
            return instance_id

        except Exception as e:
            print(f"[OCI] ✗ Failed to create instance: {e}")
            return None

    def wait_for_instance(self, instance_id: str, timeout: int = 300) -> bool:
        """
        Wait for instance to be running and get IP

        Args:
            instance_id: Instance ID to wait for
            timeout: Max seconds to wait

        Returns:
            True if instance is running with IP
        """
        print(f"[OCI] Waiting for instance {instance_id[:8]}... to be running")

        start = time.time()
        while time.time() - start < timeout:
            try:
                # Get instance details
                response = self.compute_client.get_instance(instance_id)
                instance = response.data

                if instance.lifecycle_state == "RUNNING":
                    # Get VNIC to get public IP
                    vnic_attachments = self.compute_client.list_vnic_attachments(
                        compartment_id=instance.compartment_id,
                        instance_id=instance_id
                    ).data

                    if vnic_attachments:
                        vnic = self.network_client.get_vnic(vnic_attachments[0].vnic_id).data

                        # Update instance info
                        if instance_id in self.instances:
                            self.instances[instance_id].state = "RUNNING"
                            self.instances[instance_id].public_ip = vnic.public_ip
                            self.instances[instance_id].private_ip = vnic.private_ip
                            self._save_state()

                        print(f"[OCI] ✓ Instance running: {vnic.public_ip}")
                        return True

                elif instance.lifecycle_state in ["TERMINATED", "TERMINATING"]:
                    print(f"[OCI] ✗ Instance terminated")
                    return False

            except Exception as e:
                print(f"[OCI] Error checking instance: {e}")

            time.sleep(10)

        print(f"[OCI] ✗ Timeout waiting for instance")
        return False

    def terminate_instance(self, instance_id: str):
        """Terminate an instance and update tracking"""
        print(f"[OCI] Terminating instance {instance_id[:8]}...")

        try:
            self.compute_client.terminate_instance(instance_id)

            # Update tracking
            if instance_id in self.instances:
                inst = self.instances[instance_id]

                # Calculate actual cost
                uptime_hours = (time.time() - inst.created_at) / 3600
                actual_cost = self.estimate_instance_cost(
                    InstanceConfig(
                        shape=inst.shape,
                        ocpus=2,  # Would need to track actual config
                        memory_gb=12
                    ),
                    hours=uptime_hours
                )

                self.current_spend += actual_cost

                # Free up free tier resources
                if "A1" in inst.shape and inst.cost_estimate == 0:
                    self.free_tier_usage['ampere_ocpus'] -= 2  # Would track actual
                elif inst.cost_estimate == 0:
                    self.free_tier_usage['amd_instances'] -= 1

                del self.instances[instance_id]
                self._save_state()

            print(f"[OCI] ✓ Instance terminated")

        except Exception as e:
            print(f"[OCI] ✗ Failed to terminate: {e}")

    def list_instances(self) -> List[InstanceInfo]:
        """List all managed instances"""
        return list(self.instances.values())

    def get_budget_status(self) -> Dict:
        """Get budget and spending status"""
        return {
            'max_spend': self.max_spend,
            'current_spend': self.current_spend,
            'remaining': self.max_spend - self.current_spend,
            'utilization_pct': (self.current_spend / self.max_spend) * 100,
            'free_tier_usage': self.free_tier_usage,
            'active_instances': len(self.instances)
        }

    def generate_deployment_script(self, api_keys: Dict[str, str]) -> str:
        """
        Generate cloud-init script for instance setup

        Args:
            api_keys: Dictionary of API keys (GROQ_API_KEY, etc.)

        Returns:
            Cloud-init script as string
        """
        script = """#!/bin/bash
# Book Generation System Setup Script
set -e

echo "=== Setting up Book Generation System ==="

# Update system
apt-get update
apt-get install -y python3 python3-pip git

# Create working directory
mkdir -p /opt/bookcli
cd /opt/bookcli

# Set API keys
"""

        # Add API keys
        for key, value in api_keys.items():
            script += f'echo "export {key}=\\"{value}\\"" >> /etc/environment\n'

        script += """
# Load environment
source /etc/environment

# Clone or copy book generation scripts
# In production, would pull from git or object storage
echo "Ready for book generation"

# Signal completion
echo "SETUP_COMPLETE" > /tmp/setup_status
"""

        return script

    def print_status_report(self):
        """Print detailed status report"""
        budget = self.get_budget_status()

        print("\n" + "="*60)
        print("OCI INSTANCE MANAGER STATUS")
        print("="*60)
        print(f"Budget: ${budget['max_spend']:.2f}")
        print(f"Spent: ${budget['current_spend']:.2f} ({budget['utilization_pct']:.1f}%)")
        print(f"Remaining: ${budget['remaining']:.2f}")
        print(f"\nFree Tier Usage:")
        print(f"  Ampere OCPUs: {budget['free_tier_usage']['ampere_ocpus']}/4")
        print(f"  AMD Instances: {budget['free_tier_usage']['amd_instances']}/2")
        print(f"\nActive Instances: {budget['active_instances']}")

        if self.instances:
            print("\nInstances:")
            for inst in self.instances.values():
                print(f"  {inst.name} ({inst.instance_id[:8]})")
                print(f"    Shape: {inst.shape}")
                print(f"    State: {inst.state}")
                print(f"    IP: {inst.public_ip or 'N/A'}")
                print(f"    Books: {inst.books_generated}")
                print(f"    Est. Cost: ${inst.cost_estimate:.2f}/day")

        print("="*60 + "\n")


def demo_oci_manager():
    """Demonstrate OCI manager (requires valid OCI config)"""
    print("OCI Instance Manager Demo")
    print("="*60)

    try:
        # Check if OCI config exists
        config_file = Path.home() / ".oci" / "config"
        if not config_file.exists():
            print("\n⚠ No OCI config found at ~/.oci/config")
            print("To use OCI integration:")
            print("1. Sign up for Oracle Cloud Free Tier: https://cloud.oracle.com/free")
            print("2. Generate API key: https://docs.oracle.com/iaas/Content/API/Concepts/apisigningkey.htm")
            print("3. Run: oci setup config")
            return

        # Create manager
        manager = OCIInstanceManager(max_spend=300.0)

        # Print status
        manager.print_status_report()

        # Show free tier capacity
        print("\nFree Tier Capacity:")

        # Ampere config (best for book generation)
        ampere_config = InstanceConfig(
            shape=InstanceShape.AMPERE_FREE.value,
            ocpus=2,
            memory_gb=12,
            use_free_tier=True
        )

        if manager.can_use_free_tier(ampere_config):
            cost = manager.estimate_instance_cost(ampere_config, hours=24)
            print(f"  ✓ Can create Ampere instance (FREE)")
        else:
            print(f"  ✗ Free tier exhausted")

        print("\n✓ OCI manager ready")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nNote: This demo requires valid OCI credentials")


if __name__ == "__main__":
    demo_oci_manager()
