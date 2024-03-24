# Project 5: Flowlet-based Load Balancing

## Objectives

- Understand the concept of flowlets and detect flowlets in real-traffic
- Understand the benefits of flowlet based load balancing

## Getting Started

To start this project, you will first need to get the [infrastructure setup](https://github.com/minlanyu/cs145-site/blob/spring2024/infra.md) and clone this repository with submodules
```
git clone --recurse-submodules <your repository>
```

Run `./pull_update.sh` to pull project updates (if any). You might need to merge conflicts manually: most of the time, you just need to accept incoming changes; reach to TF if it is hard to merge. This step also applies to all subsequent projects. 


- In Project 5, we provide you with the skeleton P4 script files (`TODO`), the completed controller script (`Completed`), and the completed topology file (`Completed`), enabling you to build the flowlet on top of that. It will also work if you choose to inherit your `p4src/l3fwd.p4`, `topology/p4app_fat.json` (Fattree with k=4), and `controller/controller_fat_l3.py` files from Project 3.
- We encourage you to revisit `p4_explanation.md` in project 3 for references if you incur P4 related questions in this project.

## Introduction

We implemented ECMP in Project 3. But one drawback of ECMP is that ECMP may hash two large flows onto the same path, which causes congestion. The purpose of this project is to divide large flows into smaller *flowlets* and run load balancing based on those flowlets (instead of flows). Flowlet switching leverages the burstness of TCP flows to achieve better load balancing. TCP flows tend to come in bursts (because TCP is window based). Every time there is gap which is big enough (e.g., 50ms) between packets from the same flow, flowlet switching will rehash the flow to another path (by hashing an flowlet ID value together with the 5-tuple). For more information about flowlet switching check out this [paper](https://www.usenix.org/system/files/conference/nsdi17/nsdi17-vanini.pdf).

## Part One: Flowlet Switching

In this part, you are expected to implement flowlet switching. 
You need to modify `p4src/flowlet_switching.p4` to implement flowlet switching. 

The original ECMP hashes on 5 tuples of a flow to select paths. Now with flowlets, we hash on not only the 5 tuples of a flow but also its flowlet IDs so we can select different paths for flowlets of the same flow. Here is the concrete workflow:

1. We identify flowlets by maintaining the timestamp of the last seen packet of each 5-tuple flow. You can use `standard_metadata.ingress_global_timestamp` to get the current timestamp (in micro-second) in the P4 switch. You can maintain these timestamps for each flow in a hash table. You may consider setting a large hash table size, e.g, 8192, so that you do not need to handle hash collision.
2. We define the flowlet timeout as how long a flowlet remains active. If the next packet takes more than the flowlet timeout time to arrive, we treat it as the start of a new flowlet. We suggest you set flowlet timeout as **50ms** in your experiments. Whenever the difference between the current timestamp and the last timestamp is larger than the gap, then you should treat the packet as the starting packet of a new flowlet.
3. For each new flowlet, assign it with a random flowlet ID. A large flow can have many flowlets sometimes even over a thousand. Register with of 16 bits should be fine for storing a flowlet ID. Anything larger also should not be an issue. You can use `random(val, (bit<32>)0, (bit<32>)65000)` to get a random number from 0 to 65000, and the value is written to `val`.
4. Use hash function to compute hash value for a combination of five tuples and the flowlet ID. Then use the hash value as the new ecmp group ID (due to modulo, this new ID might be the same as the old one; but overall, flowlets are distributed among all path evenly). This new ECMP group ID determines which port the switch forwards this packet to. 
5. Consider whether or not to modify the controller code.

## Hints
This code snippet provides an example of how to use registers in P4. We read from a register, compare its value with packet global timestamps, and write the timestamp back to the register.

```
struct metadata {
    bit<16> register_index;
}

control MyIngress(inout headers hdr, inout metadata meta,
                  inout standard_metadata_t standard_metadata) {
    
    /* Declare a set of registers with a size of 8192 */
    register<bit<48>>(8192) my_register;

    /* Define an action to update the registers */
    action update_register() {
        bit<48> dst_data;
        
        /* Read the content of the register with the index specified in metadata to dst_data */
        my_register.read(dst_data, (bit<32>)meta.register_index);
        
        /* If the stored data in the register has a smaller value compared to the global timestamp */
        if (standard_metadata.ingress_global_timestamp > dst_data) {

            /* Update the register with the global timestamp value */
            my_register.write((bit<32>)meta.register_index, standard_metadata.ingress_global_timestamp);

        }
    }

    apply {
        if (hdr.ipv4.isValid()){
            
            /* Call the update_register action to update the register conditionally */
            update_register();
        }
    }
}
```

### Testing
Your code should work for the following testing. These are also good steps for debugging.
1. Run your `p4src/flowlet_switching.p4`
```
sudo p4run --conf topology/p4app_fat_flowlet.json
```
2. Start your controller
```
python controller/controller_flowlet.py
```
3. Testing connectivity:
- Run `pingall`.
4. In the first testing script, it starts multiple flows in the network. If your setup effectively balances the traffic between different flows, as intended with original ECMP, then you should pass this test:
- Run `sudo python3 tests/validate_ecmp.py`. 
5. The second testing script tests Flowlet-based ECMP. Each test case involves only one flow at a time. If your implementation of Flowlet ECMP is accurate, you should be able to pass this test:
- Run `sudo python3 tests/validate_flowlet.py`. 


## Part Two: Compare Performance

In this part, let's compare the ECMP performance with flowlet switching (Your solution in Part One) and without flowlets (Project 3 solution) when network hotspots are encountered. 

1. Run ECMP without flowlet switching. Run your code in project 3:
    1. Run your `p4src/ecmp.p4`
    ```
    sudo p4run --conf topology/fat_tree_app_ecmp.json
    ```
    2. Start your controller 
    ```
    python controller/controller_fat_ecmp.py
    ```   
    3. Send two iPerf flows with our provided script. (Flow 1: from h1 to h13, and Flow 2: from h3 to h16).
    ```
    python apps/project5_send_traffic.py [duration_in_seconds] [random_seed] 
    ```
    The `random_seed` is used to generate random source and destination ports for the two flows. Since the ECMP hashing depends on the ports, you can tune the `random_seed` to make sure the two flows collide and thus generate network hotspot on the collided link. 
    
    4. You can check the iperf throughput values in the `log` directory or in the stdout to verify if the chosen paths have collided. The throughput drops significantly when collision happens. 

**Note**: To get reliable performance numbers for this project (and all future projects that need to measure throughput and latency), you'd better check your VM CPU usage and ensure it's low. You can reduce CPU usage by terminating unnecessarily running applications in your VM and your computer.

2. Run ECMP with flowlet switching. Run your code in Part One in the same way as Step 1. 
   1. Run your `p4src/flowlet_switching.p4`
   ```
   sudo p4run --conf topology/p4app_fat_flowlet.json
   ```
   2. Start your controller
   ```
   python controller/controller_flowlet.py
   ```
   3. Send two iPerf flows with our provided script. (Flow 1: from h1 to h13, and Flow 2: from h3 to h16).
   ```
    python apps/project5_send_traffic.py [duration_in_seconds] [random_seed] 
   ```
   4. You can check the iperf throughput values in the `log` directory or in the stdout to verify if the throughput drops and the chosen paths have collided. Otherwise, change your `random_seed` in step 3. 

3. Report the throughput of both flows in Step 1 and Step 2. In the report, write down the reasons on why you see the throughput difference. 

4. We now use the packet level traces collected at switches to understand the throughput difference more. We discuss how to use pcap files to parse packet traces below. Your job is to use the pcap files to answer the following questions in your report.
   1. List all the flowlets in flow 1 and flow 2 in our Step 2 experiment. You can identify the flowlets based on five tuples and packet timestamps.
   2. Identify the paths these flowlet takes. What's the percentage of flowlets of flow 1 on each of the four paths? What's the percentage of flowlets of flow 2 on each of the four paths?

### Parsing Pcap Files

When you send traffic, we record all the packets arriving at or leaving all interfaces at all switchees in the pcap files in the `pcap` directory. The name of each pcap file is in this format: `{sw_name}-{intf_name}_{in/out}.pcap`. For example, if the pcap file is `a1-eth1_in.pcap`, the file records all packets **leaving** the `eth1` interface of switch `a1`. If the pcap file is `t2-eth3_out.pcap`, the file records all packets **arriving in** the `eth3` interface of switch `t2`.

Pcap files are in binary format, so you need to use `tcpdump` to parse those files.

```
tcpdump -enn -r [pcap file] > res.txt
```

Then you can get a human-readable file `res.txt` containing the information of each packet. Within this file, each line represents one packet. For example 

```
13:29:40.413988 00:00:00:09:11:00 > 00:00:00:00:09:00, ethertype IPv4 (0x0800), length 9514: 10.0.0.5.41456 > 10.0.0.1.5001: Flags [.], seq 71136:80584, ack 1, win 74, options [nop,nop,TS val 4116827540 ecr 1502193499], length 9448
```

Each field represents timestamp, src MAC address, dst MAC address, ethernet type, packet size, src IP address/TCP port, dst IP address/TCP port, TCP flags, sequence number, ACK number, etc.

For more information about pcap, please refer to [pcap for Tcpdump page](https://www.tcpdump.org/pcap.html).

## Extra Credit 

One critical parameter in flowlet switching is the flowlet timeout , which impacts the performance of flowlet switching a lot. You can explore the impact of different timeout values based on this flowlet [paper](https://www.usenix.org/system/files/conference/nsdi17/nsdi17-vanini.pdf).
For example, you can draw a figure with different flowlet timeout values as x-axis, and corresponding iperf average throughput as y-axis. Write down your findings and embed the figure in your `report.md`. 

## Submission and Grading

### What to Submit

You are expected to submit the following documents:

1. Code: The main P4 code should be in `p4src/flowlet_switching.p4`, while you can also use other file to define headers or parsers, in order to reduce the length of each P4 file; The controller code should be in `controller_flowlet.py` which fills in table entries when launching those P4 switches.

2. report/report.md: You should describe how you implement flowlet switching and provide a detailed report on performance analysis as described above in `report.md`. You might include your findings and figure if you choose to explore different flowlet timeout value.

### Grading

The total grades is 100:

- 30: For your description of how you program in `report.md`.
- 70: We will check the correctness of your solutions for flowlet switching.
- **10**: Extra credit for exploring different flowlet timeout value. 
- Deductions based on late policies


### Survey

Please fill out the Canvas survey after completing this project. 2 extra points will be given once you have finished it. 