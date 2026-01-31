## all-reduce Benchmark

  To start the all-reduce benchmark:
    
    oc apply -f python-benchmark-optimized.yaml

  Follow the logs of the pods, the 0th pod will have results once the benchmark completes 

  To stop the benchmark:
    
    oc delete -f python-benchmark-optimized.yaml

  Note: This yaml needs two H100 node names specified. You can edit it to suit your nodes. Or make a template and submit a PR.  



