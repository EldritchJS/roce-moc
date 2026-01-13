import json
import re
import sys

def parse_rdma_file(file_path):
    try:
        with open(file_path, 'r') as f:
            for line in f:
                # We only care about the line starting with network-status
                if 'k8s.v1.cni.cncf.io/network-status' in line:
                    # 1. Extract the string between the first and last double quotes
                    # This removes the 'k8s.v1.cni.cncf.io/network-status=' prefix
                    json_payload = line.split('=', 1)[1].strip().strip('"')
                    
                    # 2. Unescape the internal characters
                    # Kubernetes writes \" and \n into the file
                    clean_json = json_payload.replace('\\"', '"').replace('\\n', '')
                    
                    # 3. Parse and Print
                    networks = json.loads(clean_json)
                    
                    print(f"{'IFACE':<8} {'IP ADDRESS':<15} {'RDMA DEVICE'}")
                    print("-" * 40)
                    
                    for net in networks:
                        name = net.get('interface', 'eth0')
                        ip = net.get('ips', ['N/A'])[0]
                        # Digging deep for the mlx5_x name
                        rdma = net.get('device-info', {}).get('pci', {}).get('rdma-device', 'N/A')
                        print(f"{name:<8} {ip:<15} {rdma}")
                    
                    return # Exit once we find the right line

        print("Error: Could not find network-status annotation in file.", file=sys.stderr)

    except Exception as e:
        print(f"Failed to parse: {e}", file=sys.stderr)

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "/etc/podinfo/annotations"
    parse_rdma_file(target)


