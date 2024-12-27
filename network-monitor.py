#!/usr/bin/env python3
import subprocess
import datetime
import json
import time
import os
import platform
import speedtest
import logging
from ping3 import ping
from scapy.all import ARP, Ether, srp
import pandas as pd
from pathlib import Path

class NetworkMonitor:
    def __init__(self, router_ip="192.168.1.1", log_dir="network_logs"):
        self.router_ip = router_ip
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Setup logging
        logging.basicConfig(
            filename=self.log_dir / "network_monitor.log",
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Create CSV files for different metrics
        self.ping_file = self.log_dir / "ping_history.csv"
        self.speed_file = self.log_dir / "speed_history.csv"
        self.devices_file = self.log_dir / "device_history.csv"
        
        # Initialize CSV files if they don't exist
        self._initialize_csv_files()

    def _initialize_csv_files(self):
        """Initialize CSV files with headers if they don't exist."""
        if not self.ping_file.exists():
            pd.DataFrame(columns=['timestamp', 'latency', 'packet_loss']).to_csv(self.ping_file, index=False)
        if not self.speed_file.exists():
            pd.DataFrame(columns=['timestamp', 'download_mbps', 'upload_mbps']).to_csv(self.speed_file, index=False)
        if not self.devices_file.exists():
            pd.DataFrame(columns=['timestamp', 'device_ip', 'device_mac', 'status']).to_csv(self.devices_file, index=False)

    def check_ping(self, count=4):
        """Check ping to router and common DNS servers."""
        targets = [self.router_ip, "8.8.8.8", "1.1.1.1"]
        results = {}
        
        for target in targets:
            try:
                latencies = []
                for _ in range(count):
                    response_time = ping(target, timeout=1)
                    if response_time is not None:
                        latencies.append(response_time * 1000)  # Convert to ms
                
                if latencies:
                    avg_latency = sum(latencies) / len(latencies)
                    packet_loss = (count - len(latencies)) / count * 100
                else:
                    avg_latency = None
                    packet_loss = 100
                    
                results[target] = {
                    'latency': avg_latency,
                    'packet_loss': packet_loss
                }
                
                # Log to CSV
                pd.DataFrame({
                    'timestamp': [datetime.datetime.now()],
                    'latency': [avg_latency],
                    'packet_loss': [packet_loss]
                }).to_csv(self.ping_file, mode='a', header=False, index=False)
                
            except Exception as e:
                self.logger.error(f"Error pinging {target}: {str(e)}")
                results[target] = {'error': str(e)}
        
        return results

    def check_speed(self):
        """Run a speed test and log results."""
        try:
            st = speedtest.Speedtest()
            self.logger.info("Running speed test...")
            
            # Get best server
            st.get_best_server()
            
            # Run speed test
            download_speed = st.download() / 1_000_000  # Convert to Mbps
            upload_speed = st.upload() / 1_000_000  # Convert to Mbps
            
            # Log results
            pd.DataFrame({
                'timestamp': [datetime.datetime.now()],
                'download_mbps': [download_speed],
                'upload_mbps': [upload_speed]
            }).to_csv(self.speed_file, mode='a', header=False, index=False)
            
            return {
                'download_mbps': round(download_speed, 2),
                'upload_mbps': round(upload_speed, 2)
            }
            
        except Exception as e:
            self.logger.error(f"Speed test error: {str(e)}")
            return {'error': str(e)}

    def scan_network_devices(self):
        """Scan for active devices on the network."""
        try:
            # Create ARP request packet
            arp = ARP(pdst=f"{self.router_ip}/24")
            ether = Ether(dst="ff:ff:ff:ff:ff:ff")
            packet = ether/arp

            # Send packet and get response
            result = srp(packet, timeout=3, verbose=0)[0]
            
            # Process devices
            devices = []
            for sent, received in result:
                devices.append({
                    'ip': received.psrc,
                    'mac': received.hwsrc,
                    'status': 'active'
                })
                
            # Log to CSV
            now = datetime.datetime.now()
            devices_df = pd.DataFrame(devices)
            devices_df['timestamp'] = now
            devices_df.to_csv(self.devices_file, mode='a', header=False, index=False)
            
            return devices
            
        except Exception as e:
            self.logger.error(f"Network scan error: {str(e)}")
            return {'error': str(e)}

    def generate_report(self):
        """Generate a summary report of network status."""
        try:
            report = {
                'timestamp': datetime.datetime.now().isoformat(),
                'ping_tests': self.check_ping(),
                'speed_test': self.check_speed(),
                'active_devices': self.scan_network_devices()
            }
            
            # Save report
            report_file = self.log_dir / f"report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=4)
            
            return report
            
        except Exception as e:
            self.logger.error(f"Report generation error: {str(e)}")
            return {'error': str(e)}

def main():
    # Initialize monitor
    monitor = NetworkMonitor()
    
    while True:
        try:
            # Generate report
            report = monitor.generate_report()
            
            # Print summary
            print("\n=== Network Status Report ===")
            print(f"Time: {datetime.datetime.now()}")
            
            # Print ping results
            print("\nPing Results:")
            for target, results in report['ping_tests'].items():
                if 'error' not in results:
                    print(f"{target}: {results['latency']:.1f}ms ({results['packet_loss']}% loss)")
                else:
                    print(f"{target}: Error - {results['error']}")
            
            # Print speed test results
            print("\nSpeed Test Results:")
            if 'error' not in report['speed_test']:
                print(f"Download: {report['speed_test']['download_mbps']} Mbps")
                print(f"Upload: {report['speed_test']['upload_mbps']} Mbps")
            else:
                print(f"Speed test error: {report['speed_test']['error']}")
            
            # Print device count
            if isinstance(report['active_devices'], list):
                print(f"\nActive Devices: {len(report['active_devices'])}")
            
            # Wait for next check
            print("\nWaiting 5 minutes for next check...")
            time.sleep(300)  # 5 minutes
            
        except KeyboardInterrupt:
            print("\nMonitoring stopped by user")
            break
        except Exception as e:
            print(f"Error in main loop: {str(e)}")
            time.sleep(60)  # Wait 1 minute before retrying

if __name__ == "__main__":
    main()