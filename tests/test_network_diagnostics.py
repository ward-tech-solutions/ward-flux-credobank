import math

from network_diagnostics import NetworkDiagnostics


def test_parse_ping_unix_handles_decimal_packet_loss():
    sample_output = """
    PING 8.8.8.8 (8.8.8.8): 56 data bytes
    64 bytes from 8.8.8.8: icmp_seq=0 ttl=118 time=41.931 ms
    64 bytes from 8.8.8.8: icmp_seq=1 ttl=118 time=45.002 ms
    64 bytes from 8.8.8.8: icmp_seq=2 ttl=118 time=52.921 ms

    --- 8.8.8.8 ping statistics ---
    5 packets transmitted, 4 packets received, 20.0% packet loss
    round-trip min/avg/max/stddev = 41.931/45.002/52.921/4.328 ms
    """

    diag = NetworkDiagnostics()
    parsed = diag._parse_ping_unix(sample_output, "8.8.8.8", 5)

    assert parsed["packets_sent"] == 5
    assert parsed["packets_received"] == 4
    assert math.isclose(parsed["packet_loss_percent"], 20.0)
    assert parsed["is_reachable"] is True
    assert math.isclose(parsed["min_rtt_ms"], 41.931)
    assert math.isclose(parsed["avg_rtt_ms"], 45.002)
    assert math.isclose(parsed["max_rtt_ms"], 52.921)
