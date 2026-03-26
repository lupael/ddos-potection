// SPDX-License-Identifier: GPL-2.0
/*
 * xdp_ddos_filter.c — XDP eBPF DDoS filter skeleton
 *
 * Compile with:
 *   clang -O2 -target bpf -c xdp_ddos_filter.c -o xdp_ddos_filter.o
 */

#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/tcp.h>
#include <linux/udp.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_endian.h>

/* Map: source IPv4 address -> blocked flag (1 = blocked) */
struct {
    __uint(type, BPF_MAP_TYPE_LRU_HASH);
    __type(key,   __u32);   /* source IP (network byte order) */
    __type(value, __u8);    /* 1 = blocked */
    __uint(max_entries, 65536);
} blocked_ips SEC(".maps");

/*
 * TCP SYN-flood stub counter map.
 * Key: source IP, Value: SYN packet count in current window.
 * TODO: implement sliding-window logic in user-space controller.
 */
struct {
    __uint(type, BPF_MAP_TYPE_LRU_PERCPU_HASH);
    __type(key,   __u32);
    __type(value, __u64);
    __uint(max_entries, 65536);
} syn_counters SEC(".maps");

SEC("xdp")
int ddos_filter(struct xdp_md *ctx)
{
    void *data_end = (void *)(long)ctx->data_end;
    void *data     = (void *)(long)ctx->data;

    /* Parse Ethernet header */
    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end)
        return XDP_PASS;

    if (bpf_ntohs(eth->h_proto) != ETH_P_IP)
        return XDP_PASS;

    /* Parse IPv4 header */
    struct iphdr *ip = (void *)(eth + 1);
    if ((void *)(ip + 1) > data_end)
        return XDP_PASS;

    __u32 src_ip = ip->saddr;

    /* Check blocked_ips map */
    __u8 *blocked = bpf_map_lookup_elem(&blocked_ips, &src_ip);
    if (blocked && *blocked == 1)
        return XDP_DROP;

    /* TCP SYN-flood threshold stub */
    if (ip->protocol == IPPROTO_TCP) {
        struct tcphdr *tcp = (void *)((__u8 *)ip + (ip->ihl * 4));
        if ((void *)(tcp + 1) > data_end)
            return XDP_PASS;

        if (tcp->syn && !tcp->ack) {
            /*
             * TODO: increment syn_counters[src_ip] and drop if the count
             * exceeds the configured SYN_FLOOD_THRESHOLD within the window.
             * The user-space controller resets counts periodically.
             */
        }
    }

    return XDP_PASS;
}

char _license[] SEC("license") = "GPL";
