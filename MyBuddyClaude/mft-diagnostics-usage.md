# MFT Diagnostics Pod - Usage Guide

## Deployment

**Image:** `quay.io/jschless/mft-diagnostics:latest` (publicly available)

Deploy the diagnostics pod on a specific node:

```bash
oc process -f mft-diagnostics-pod-template.yaml \
  -p NODE_NAME=<NODE NAME> | oc apply -f -
```

**Startup time:** ~5 seconds (vs 2+ minutes with runtime installation)

## Access the Pod

```bash
oc exec -it mft-diagnostics -- bash
```

## Available Tools

### ✅ MFT (Mellanox Firmware Tools)
- `mst status` - Show MST PCI devices
- `mlxconfig -d <dev> query` - Query firmware configuration
- `mlxconfig -d <dev> set <param>=<value>` - Change firmware settings
- `mstflint -d <dev> query` - Query firmware version

### ✅ RDMA/InfiniBand Diagnostics
- `ibstat` - Show IB port status and state
- `ibv_devinfo` - Show detailed RDMA device info
- `ibv_devices` - List all RDMA devices
- `perfquery` - Query IB performance counters
- `ibdev2netdev` - Map IB devices to network interfaces

### ✅ OFED Utilities
- `ofed_info` - Show OFED version information
- `ofed_info -s` - Short version info

## Common Commands

### 1. List MST Devices
```bash
mst status
```

Output shows PCI addresses like: `03:00.0`, `c3:00.0`, etc.

### 2. Query NIC Firmware Configuration
```bash
# Use PCI address from mst status
mlxconfig -d 03:00.0 query

# Check specific parameter
mlxconfig -d 03:00.0 query | grep NUM_OF_VFS
mlxconfig -d 03:00.0 query | grep SRIOV_EN
```

### 3. List RDMA Devices
```bash
ibv_devices
```

### 4. Check RDMA Device Details
```bash
# Detailed info for specific device
ibv_devinfo mlx5_X

# Verbose output
ibv_devinfo -v mlx5_X
```

### 5. Check IB Port Status
```bash
ibstat

# For specific device
ibstat mlx5_X
```

### 6. Map RDMA Devices to Network Interfaces

**Method 1 - Using ibdev2netdev (Recommended):**
```bash
ibdev2netdev
```

Output:
```
mlx5_0 port 1 ==> eno2np0 (Up)
mlx5_1 port 1 ==> eno3np1 (Down)
mlx5_2 port 1 ==> eno6np0 (Up)
mlx5_3 port 1 ==> eno5np0 (Up)
mlx5_4 port 1 ==> eno8np0 (Up)
mlx5_5 port 1 ==> eno7np0 (Up)
mlx5_6 port 1 ==> eno5v0 (Down)  # SR-IOV VF
mlx5_7 port 1 ==> eno6v0 (Down)  # SR-IOV VF
```

**Method 2 - Using sys filesystem:**
```bash
for dev in /sys/class/infiniband/*; do
  dev_name=$(basename $dev)
  port_state=$(cat $dev/ports/1/state 2>/dev/null || echo "N/A")
  netdev=$(ls $dev/device/net/ 2>/dev/null)
  echo "$dev_name => $netdev (port state: $port_state)"
done
```

**Method 3 - Manual check:**
```bash
# List RDMA devices
ibv_devices

# List network interfaces
ip link show | grep mlx
ls -la /sys/class/net/
```

### 7. Check OFED Version
```bash
# Show OFED version
ofed_info -s

# Full OFED info
ofed_info
```

### 8. Check SR-IOV Configuration
```bash
# Check if SR-IOV is enabled
mlxconfig -d 03:00.0 query | grep SRIOV_EN

# Check number of VFs configured
mlxconfig -d 03:00.0 query | grep NUM_OF_VFS
```

## Cleanup

```bash
oc delete pod mft-diagnostics -n nccl-test
```
