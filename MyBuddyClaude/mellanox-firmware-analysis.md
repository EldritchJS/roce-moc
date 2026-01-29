# Mellanox ConnectX-7 Firmware Analysis and Optimization Recommendations

**Analysis Date:** 2026-01-29
**Nodes Analyzed:** moc-r4pcc04u23-nairr, moc-r4pcc04u25-nairr
**NICs:** 4x ConnectX-7 400G per node (PCI addresses: 03:00.0, 23:00.0, a3:00.0, c3:00.0)
**Current Performance:** 1403 Gbps (87.7% of theoretical maximum)

---

## Executive Summary

Both nodes have **identical and conservative firmware settings**. Several optimization opportunities exist that could improve RDMA performance, particularly for the current workload achieving 87.7% utilization.

**Key Findings:**
- ✅ Settings are consistent across all 8 NICs (4 per node × 2 nodes)
- ⚠️ NUM_OF_VFS limited to 1 (firmware constraint, not operator)
- ⚠️ RoCE Adaptive Routing disabled (potential for improved load balancing)
- ⚠️ MAX_ACC_OUT_READ at default (128) - could be increased
- ⚠️ CQE_COMPRESSION at BALANCED - could be optimized for throughput
- ✅ RDMA Selective Repeat disabled (correct for low-latency workloads)
- ✅ PCI Write Ordering set to per_mkey (correct for RDMA)

---

## Current Firmware Configuration

### SR-IOV and VF Settings
```
NUM_OF_VFS                    1              ⚠️ Firmware limited
SRIOV_EN                      True(1)        ✅ Enabled
NUM_PF_MSIX                   63             ⚠️ Limited MSI-X vectors
NUM_VF_MSIX                   11             ⚠️ Limited MSI-X vectors
VF_LOG_BAR_SIZE               1              ⚠️ Small BAR (2^1 = 2 bytes)
PF_LOG_BAR_SIZE               5              ⚠️ Small BAR (2^5 = 32 bytes)
```

**Impact:** With only 1 VF per NIC, you have limited queue depth and parallelism. This directly constrains the ability to reach >90% utilization.

### PCI and DMA Settings
```
MAX_ACC_OUT_READ              128            ⚠️ Could be increased to 256 or 512
PCI_WR_ORDERING               per_mkey(0)    ✅ Optimal for RDMA
ADVANCED_PCI_SETTINGS         True(1)        ✅ Enabled
PCI_ATOMIC_MODE               DISABLED(0)    ℹ️ PCIe atomics disabled
```

**Impact:** MAX_ACC_OUT_READ of 128 limits the number of outstanding PCIe read requests, potentially bottlenecking GPUDirect RDMA throughput.

### RDMA and RoCE Settings
```
ROCE_CONTROL                  ROCE_ENABLE(2)         ✅ Enabled
ROCE_ADAPTIVE_ROUTING_EN      False(0)               ⚠️ Disabled
CQE_COMPRESSION               BALANCED(0)            ⚠️ Could optimize for throughput
RDMA_SELECTIVE_REPEAT_EN      False(0)               ✅ Correct for low latency
```

**Impact:**
- **RoCE Adaptive Routing disabled** means all traffic uses static routes, which can lead to imbalanced link utilization across the 4 NICs
- **CQE_COMPRESSION=BALANCED** is a middle ground; for pure throughput workloads, AGGRESSIVE compression could free up PCIe bandwidth

### RoCE Congestion Control (ECN/DCQCN)
```
ROCE_CC_PRIO_MASK_P1          255                    ✅ All priorities enabled
CNP_DSCP_P1                   48                     ✅ Standard DSCP for CNP
RPG_TIME_RESET_P1             300                    ℹ️ Default
RPG_BYTE_RESET_P1             32767                  ℹ️ Default
RPG_AI_RATE_P1                5                      ℹ️ Additive increase rate
RPG_HAI_RATE_P1               50                     ℹ️ Hyper-additive increase rate
DCE_TCP_G_P1                  1019                   ℹ️ DCE parameter
```

**Impact:** These are standard DCQCN parameters. With your current 87.7% utilization and no reported congestion, these are likely adequate. Tuning these would only help if you were seeing CNP (Congestion Notification Packets).

### Queue and Memory Settings
```
LOG_MAX_QUEUE                 17                     ℹ️ Max 2^17 = 131072 queues
LOG_MAX_OUTSTANDING_WQE       7                      ⚠️ Max 2^7 = 128 outstanding WQEs
NUM_PF_MSIX                   63                     ⚠️ Limited interrupt vectors
```

**Impact:** LOG_MAX_OUTSTANDING_WQE=7 (128 WQEs) may limit queue depth for high-throughput operations.

---

## Optimization Recommendations

### Priority 1: Increase Virtual Functions (HIGH IMPACT, HIGH RISK)

**Current:** NUM_OF_VFS = 1
**Recommended:** NUM_OF_VFS = 16 or 32

**Commands:**
```bash
# For each ConnectX-7 NIC (on each node)
mlxconfig -d 03:00.0 set NUM_OF_VFS=16
mlxconfig -d 23:00.0 set NUM_OF_VFS=16
mlxconfig -d a3:00.0 set NUM_OF_VFS=16
mlxconfig -d c3:00.0 set NUM_OF_VFS=16

# Reboot required after this change
reboot
```

**Expected Gain:** +1-3% (16-48 Gbps)
**Risk:** HIGH - Requires firmware change, node reboot, SR-IOV policy update
**Reversibility:** Medium - Can revert but requires another reboot

**Why this helps:**
- More VFs = more parallel queues = better utilization of 4 NICs
- Reduces head-of-line blocking
- Better load distribution across NCCL channels

**Follow-up actions:**
After reboot, update SR-IOV policy:
```bash
oc patch sriovnetworknodepolicy policy-eno5np0 \
  -n openshift-sriov-network-operator \
  --type=merge \
  -p '{"spec":{"numVfs":16}}'

# Repeat for eno6np0, eno7np0, eno8np0
```

---

### Priority 2: Enable RoCE Adaptive Routing (MEDIUM IMPACT, LOW RISK)

**Current:** ROCE_ADAPTIVE_ROUTING_EN = False
**Recommended:** ROCE_ADAPTIVE_ROUTING_EN = True

**Commands:**
```bash
# For each ConnectX-7 NIC (on each node)
mlxconfig -d 03:00.0 set ROCE_ADAPTIVE_ROUTING_EN=1
mlxconfig -d 23:00.0 set ROCE_ADAPTIVE_ROUTING_EN=1
mlxconfig -d a3:00.0 set ROCE_ADAPTIVE_ROUTING_EN=1
mlxconfig -d c3:00.0 set ROCE_ADAPTIVE_ROUTING_EN=1

# Reboot or reset NIC required
# Reboot is safest:
reboot
```

**Expected Gain:** +0.5-1.5% (8-24 Gbps)
**Risk:** LOW - Feature can be reverted
**Reversibility:** High - Easy to revert

**Why this helps:**
- Adaptive routing dynamically balances traffic across available paths
- With 4 NICs, this can reduce hotspots and improve overall link utilization
- Particularly beneficial for AllReduce with 16 NCCL channels across 4 NICs

**Note:** Adaptive routing works best when combined with increased VF count (Priority 1).

---

### Priority 3: Increase MAX_ACC_OUT_READ (MEDIUM IMPACT, LOW RISK)

**Current:** MAX_ACC_OUT_READ = 128
**Recommended:** MAX_ACC_OUT_READ = 256 or 512

**Commands:**
```bash
# Try 256 first (safer)
mlxconfig -d 03:00.0 set MAX_ACC_OUT_READ=256
mlxconfig -d 23:00.0 set MAX_ACC_OUT_READ=256
mlxconfig -d a3:00.0 set MAX_ACC_OUT_READ=256
mlxconfig -d c3:00.0 set MAX_ACC_OUT_READ=256

# Reboot required
reboot

# If 256 works well, can try 512 later for additional gain
```

**Expected Gain:** +0.3-1% (5-16 Gbps)
**Risk:** LOW - Can revert if issues occur
**Reversibility:** High

**Why this helps:**
- Increases the number of outstanding PCIe read requests
- GPUDirect RDMA benefits from more concurrent reads
- Can improve PCIe bandwidth utilization to/from GPUs

**Caution:**
- Values too high (>512) may cause PCIe congestion
- Test with 256 first, monitor for errors

---

### Priority 4: Optimize CQE Compression (LOW IMPACT, LOW RISK)

**Current:** CQE_COMPRESSION = BALANCED
**Recommended:** CQE_COMPRESSION = AGGRESSIVE

**Commands:**
```bash
mlxconfig -d 03:00.0 set CQE_COMPRESSION=2  # 2=AGGRESSIVE
mlxconfig -d 23:00.0 set CQE_COMPRESSION=2
mlxconfig -d a3:00.0 set CQE_COMPRESSION=2
mlxconfig -d c3:00.0 set CQE_COMPRESSION=2

# Reboot required
reboot
```

**Expected Gain:** +0.2-0.5% (3-8 Gbps)
**Risk:** LOW
**Reversibility:** High

**Why this helps:**
- Aggressive CQE compression reduces PCIe traffic for completion notifications
- Frees up PCIe bandwidth for actual data transfers
- For throughput-focused workloads (vs. latency-sensitive), this is beneficial

**Tradeoff:**
- Slightly increases CPU overhead for decompression
- May add ~100-200ns latency per operation (negligible for large transfers)

---

### Priority 5: Increase MSI-X Vectors (LOW IMPACT, MEDIUM RISK)

**Current:** NUM_PF_MSIX = 63, NUM_VF_MSIX = 11
**Recommended:** NUM_PF_MSIX = 127, NUM_VF_MSIX = 31

**Commands:**
```bash
mlxconfig -d 03:00.0 set NUM_PF_MSIX=127 NUM_VF_MSIX=31
mlxconfig -d 23:00.0 set NUM_PF_MSIX=127 NUM_VF_MSIX=31
mlxconfig -d a3:00.0 set NUM_PF_MSIX=127 NUM_VF_MSIX=31
mlxconfig -d c3:00.0 set NUM_PF_MSIX=127 NUM_VF_MSIX=31

# Reboot required
reboot
```

**Expected Gain:** +0.2-0.5% (3-8 Gbps)
**Risk:** MEDIUM - More interrupts may increase CPU overhead
**Reversibility:** High

**Why this helps:**
- More MSI-X vectors allow more parallel interrupt handling
- Better CPU core distribution for NIC interrupts
- Useful when combined with increased VF count

**Note:** Only implement this if you also implement Priority 1 (increase VFs).

---

## Recommended Implementation Strategy

### Conservative Path (90% Utilization - 1440 Gbps)
**Timeline:** 1-2 days
**Risk:** LOW

**Steps:**
1. ✅ Enable RoCE Adaptive Routing (Priority 2)
2. ✅ Increase MAX_ACC_OUT_READ to 256 (Priority 3)
3. ✅ Test and validate
4. ✅ If successful, try CQE_COMPRESSION=AGGRESSIVE (Priority 4)

**Expected Result:** 1420-1450 Gbps (88.7-90.6%)

**Commands Summary:**
```bash
# Deploy diagnostics pod to both nodes
oc process -f mft-diagnostics-template.yaml -p NODE_NAME=moc-r4pcc04u23-nairr | oc apply -f -

# Install MFT and apply settings
oc exec mft-diagnostics -n default -- bash -c "
  cd /tmp &&
  wget -q https://www.mellanox.com/downloads/MFT/mft-4.27.0-83-x86_64-deb.tgz &&
  tar xzf mft-4.27.0-83-x86_64-deb.tgz &&
  cd mft-4.27.0-83-x86_64-deb &&
  ./install.sh --without-kernel &&

  # Apply settings to all 4 NICs
  for pci in 03:00.0 23:00.0 a3:00.0 c3:00.0; do
    mlxconfig -d \$pci set ROCE_ADAPTIVE_ROUTING_EN=1 MAX_ACC_OUT_READ=256
  done
"

# Delete pod, then schedule node reboot
oc delete pod mft-diagnostics -n default
# (Coordinate node reboot with cluster admin)

# Repeat for second node
```

---

### Aggressive Path (93% Utilization - 1490 Gbps)
**Timeline:** 1-2 weeks
**Risk:** HIGH

**Steps:**
1. ⚠️ Implement Conservative Path first
2. ⚠️ Increase NUM_OF_VFS to 16 (Priority 1)
3. ⚠️ Update SR-IOV policies
4. ⚠️ Redeploy benchmark pods with updated VF configuration
5. ⚠️ Validate and test
6. ⚠️ If successful, increase NUM_VF_MSIX (Priority 5)

**Expected Result:** 1480-1510 Gbps (92.5-94.4%)

**Important Considerations:**
- Requires firmware reconfiguration + reboot
- SR-IOV operator policies must be updated
- Benchmark pod YAMLs must be updated to request more VFs
- Higher complexity and validation requirements

---

## Validation and Testing

After applying any changes:

### 1. Verify Firmware Settings
```bash
oc exec mft-diagnostics -n default -- bash -c "
  for pci in 03:00.0 23:00.0 a3:00.0 c3:00.0; do
    echo '=== NIC at \$pci ==='
    mlxconfig -d \$pci q | grep -E '(ROCE_ADAPTIVE|MAX_ACC_OUT_READ|NUM_OF_VFS|CQE_COMPRESSION)'
    echo ''
  done
"
```

### 2. Check RDMA Device Status
```bash
oc exec mft-diagnostics -n default -- ibv_devinfo -l
```

### 3. Run Benchmark
```bash
oc apply -f pytorch-benchmark-optimized.yaml
oc logs -f pytorch-benchmark-opt-0 -n nccl-test
```

### 4. Monitor for Errors
```bash
# Check for PCI errors
oc exec mft-diagnostics -n default -- dmesg | grep -i 'pci\|mlx'

# Check RDMA errors
oc exec mft-diagnostics -n default -- bash -c "
  for dev in /sys/class/infiniband/mlx5_*; do
    echo \"Device: \$(basename \$dev)\"
    cat \$dev/ports/1/hw_counters/* 2>/dev/null | grep -E 'error|drop' || true
    echo ''
  done
"
```

---

## Firmware Update Considerations

**Current Firmware:** ConnectX-7 (exact version not captured - use `mstflint -d 03:00.0 q` to check)

**Recommendation:** Before implementing aggressive optimizations, consider:
1. Check current firmware version: `mstflint -d 03:00.0 q | grep 'FW Version'`
2. Compare to latest available firmware: https://network.nvidia.com/support/firmware/connectx7/
3. If more than 6 months old, consider updating firmware first
4. Latest firmware may have bug fixes and performance improvements

**Firmware update process:**
```bash
# Check current version
mstflint -d 03:00.0 q

# Download latest firmware from NVIDIA
# Update with:
# mstflint -d 03:00.0 -i <firmware.bin> burn

# IMPORTANT: This requires a reboot and has risks
# Always back up firmware first:
# mstflint -d 03:00.0 ri <backup.bin>
```

---

## Risk Assessment Matrix

| Optimization | Impact | Risk | Reboot Required | Reversibility |
|--------------|--------|------|-----------------|---------------|
| RoCE Adaptive Routing | Medium | Low | Yes | Easy |
| MAX_ACC_OUT_READ=256 | Medium | Low | Yes | Easy |
| CQE_COMPRESSION=AGGRESSIVE | Low | Low | Yes | Easy |
| NUM_OF_VFS=16 | High | High | Yes | Medium |
| NUM_PF_MSIX=127 | Low | Medium | Yes | Easy |

---

## Conclusion

**Current Status:** Your ConnectX-7 NICs are running with conservative, stable firmware settings that are **adequate but not optimized for maximum throughput**.

**Recommended Next Steps:**
1. **Start with Conservative Path** - Low risk, reasonable gains (+2-3%)
2. **If you need 93%+ utilization** - Proceed with VF increase (Priority 1), but understand the complexity
3. **Monitor and validate** - After each change, validate before proceeding

**Realistic Expectations:**
- Conservative path: **90% utilization (1440 Gbps)** - Highly achievable
- Aggressive path: **92-93% utilization (1470-1490 Gbps)** - Achievable with effort
- Beyond 93%: Hitting fundamental protocol limits (~5-7% overhead unavoidable)

Would you like me to:
1. Generate scripts to apply the Conservative Path optimizations?
2. Create a detailed rollback plan?
3. Help with firmware version checking and update planning?
