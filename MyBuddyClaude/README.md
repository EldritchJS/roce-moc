## all-reduce Benchmark

  To start the all-reduce benchmark:

    `oc apply -f python-benchmark...yaml`

    Follow the logs of the pods, the 0th pod will have results once the benchmark completes 

  To stop the benchmark:

  `oc delete -f python-benchmark...yaml`

## Mellanox Firmware Settings

  To mess with Mellanox firmware settings:

    `oc process -f /Users/jschless/taj/cairo/mft-diagnostics-template.yaml  -p NODE_NAME=<NODE NAME> | oc apply -f -` 
                                                                                                                                                                                            
  Once the pod is running, you can exec into it:                                                                                                                                            
                                                                                                                                                                                            
    `oc exec -it mft-diagnostics -n nccl-test -- bash` 
 
    Then run stuff like:                                                                                                                                                                                         
    - `mst status` - Show MST devices
    - `ibdev2netdev` - Map IB devices to network interfaces
    - `mlxconfig -d mlx5_X query` - Query firmware settings
    - `ibv_devinfo mlx5_X` - Show RDMA device info                                                                                                                                              
                                                                                                                                                                                            
  To stop the pod:                                                                                                                                                                                 
    `oc delete pod mft-diagnostics -n nccl-test`       


