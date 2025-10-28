"""
WARD FLUX - ISP Fault Classification System
Intelligently determines if network faults are customer-side or ISP-side

This module provides sophisticated fault analysis to help network engineers
quickly identify the root cause of connectivity issues and take appropriate action.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class FaultType(Enum):
    """Classification of network fault origin"""
    CUSTOMER_SIDE = "customer_side"  # Issue on CredoBank side
    ISP_SIDE = "isp_side"            # Issue on ISP (Magti/Silknet) side
    UNDETERMINED = "undetermined"     # Cannot determine fault location


@dataclass
class FaultAnalysis:
    """Result of fault classification analysis"""
    fault_type: FaultType
    confidence: float  # 0.0 to 1.0 (percentage / 100)
    reason: str
    recommended_action: str
    affected_isp: Optional[str] = None
    technical_details: Optional[dict] = None


class ISPFaultClassifier:
    """
    Classifier for determining if network faults are customer-side or ISP-side

    Decision Logic:
    ================
    1. Device DOWN + Interface DOWN
       → CUSTOMER_SIDE (95% confidence)
       → Reason: Power outage, hardware failure, local network issue

    2. Device UP + Interface admin_down
       → CUSTOMER_SIDE (100% confidence)
       → Reason: Interface manually disabled by administrator

    3. Device UP + Interface DOWN + High CRC errors (>100)
       → CUSTOMER_SIDE (85% confidence)
       → Reason: Physical layer issue (bad cable, damaged port, EMI)

    4. Device UP + Interface DOWN + Low CRC errors
       → UNDETERMINED (50% confidence)
       → Reason: Could be ISP circuit down or remote equipment issue

    5. Interface UP + High error rate (>1% or >1000 errors)
       → ISP_SIDE (90% confidence)
       → Reason: ISP network congestion or quality issues

    6. Interface UP + High discard rate (>2% or >5000 discards)
       → ISP_SIDE (75% confidence)
       → Reason: Network congestion (possibly ISP-side)

    7. Interface UP + High CRC errors (>50)
       → CUSTOMER_SIDE (80% confidence)
       → Reason: Physical layer degradation even with link up
    """

    @staticmethod
    def analyze_interface_fault(
        device_ping_status: str,
        interface_oper_status: str,
        interface_admin_status: str,
        in_errors: int = 0,
        out_errors: int = 0,
        in_discards: int = 0,
        out_discards: int = 0,
        crc_errors: int = 0,
        in_octets: int = 0,
        isp_name: str = "ISP"
    ) -> FaultAnalysis:
        """
        Analyze interface fault and classify as customer-side or ISP-side

        Args:
            device_ping_status: 'Up' or 'Down'
            interface_oper_status: 'up' or 'down'
            interface_admin_status: 'up' or 'down'
            in_errors: Input errors count
            out_errors: Output errors count
            in_discards: Input discards count
            out_discards: Output discards count
            crc_errors: CRC error count
            in_octets: Input octets (for error rate calculation)
            isp_name: Name of ISP provider (e.g., 'magti', 'silknet')

        Returns:
            FaultAnalysis object with classification and recommendations
        """

        # === SCENARIO 1: Device completely down ===
        if device_ping_status == 'Down':
            return FaultAnalysis(
                fault_type=FaultType.CUSTOMER_SIDE,
                confidence=0.95,
                reason="Device unreachable via ping - indicates power outage, hardware failure, or local network issue",
                recommended_action="Check device power supply, console access, or replace hardware. Verify local network connectivity.",
                affected_isp=None,
                technical_details={
                    "device_status": "DOWN",
                    "interface_status": interface_oper_status,
                    "diagnosis": "Customer-side hardware or power issue"
                }
            )

        # === SCENARIO 2: Interface administratively down ===
        if interface_oper_status == 'down' and interface_admin_status == 'down':
            return FaultAnalysis(
                fault_type=FaultType.CUSTOMER_SIDE,
                confidence=1.0,
                reason="Interface was manually disabled by network administrator",
                recommended_action="Enable interface using 'no shutdown' command if this downtime was unintended",
                affected_isp=None,
                technical_details={
                    "admin_status": "DOWN",
                    "oper_status": "DOWN",
                    "diagnosis": "Administratively disabled interface"
                }
            )

        # === SCENARIO 3: Interface down with high CRC errors ===
        if interface_oper_status == 'down' and crc_errors > 100:
            return FaultAnalysis(
                fault_type=FaultType.CUSTOMER_SIDE,
                confidence=0.85,
                reason=f"High CRC errors ({crc_errors}) indicate physical layer issue - bad cable, damaged router port, or EMI interference",
                recommended_action="Inspect and replace network cable between router and ISP equipment. Check router port for damage. Look for sources of electromagnetic interference.",
                affected_isp=None,
                technical_details={
                    "crc_errors": crc_errors,
                    "interface_status": "DOWN",
                    "diagnosis": "Physical layer issue (cable/port)"
                }
            )

        # === SCENARIO 4: Interface down without local physical errors ===
        if interface_oper_status == 'down' and interface_admin_status == 'up':
            return FaultAnalysis(
                fault_type=FaultType.UNDETERMINED,
                confidence=0.5,
                reason="Link down with no local physical layer errors - could be ISP circuit down or remote equipment issue",
                recommended_action=f"Contact {isp_name.upper()} support to verify circuit status and remote equipment operation. Provide circuit ID and current error statistics.",
                affected_isp=isp_name,
                technical_details={
                    "crc_errors": crc_errors,
                    "interface_status": "DOWN",
                    "admin_status": "UP",
                    "diagnosis": "Link down - requires ISP investigation"
                }
            )

        # === SCENARIO 5: Interface up with high error rate ===
        if interface_oper_status == 'up':
            # Calculate error rate as percentage
            total_packets = in_octets // 64 if in_octets > 0 else 0  # Rough packet estimate
            error_rate = (in_errors / total_packets * 100) if total_packets > 0 else 0
            discard_rate = (in_discards / total_packets * 100) if total_packets > 0 else 0

            # High error rate indicates ISP network issues
            if error_rate > 1.0 or in_errors > 1000:
                return FaultAnalysis(
                    fault_type=FaultType.ISP_SIDE,
                    confidence=0.9,
                    reason=f"High input error rate ({error_rate:.2f}% or {in_errors} errors) indicates ISP network congestion or quality degradation",
                    recommended_action=f"Open support ticket with {isp_name.upper()}. Provide error statistics, timestamps, and request link quality analysis. Ask for packet loss measurements on their side.",
                    affected_isp=isp_name,
                    technical_details={
                        "error_rate_percent": round(error_rate, 2),
                        "in_errors": in_errors,
                        "total_packets_estimate": total_packets,
                        "diagnosis": "ISP network quality issue"
                    }
                )

            # High discard rate indicates congestion
            if discard_rate > 2.0 or in_discards > 5000:
                return FaultAnalysis(
                    fault_type=FaultType.ISP_SIDE,
                    confidence=0.75,
                    reason=f"High packet discard rate ({discard_rate:.2f}% or {in_discards} discards) indicates network congestion",
                    recommended_action=f"Monitor bandwidth utilization. If link is underutilized on your side, contact {isp_name.upper()} about upstream congestion. Consider bandwidth upgrade if consistently high.",
                    affected_isp=isp_name,
                    technical_details={
                        "discard_rate_percent": round(discard_rate, 2),
                        "in_discards": in_discards,
                        "diagnosis": "Network congestion (likely ISP-side)"
                    }
                )

            # High CRC errors even with link up indicates physical degradation
            if crc_errors > 50:
                return FaultAnalysis(
                    fault_type=FaultType.CUSTOMER_SIDE,
                    confidence=0.8,
                    reason=f"CRC errors ({crc_errors}) present even with link up - indicates physical layer degradation (cable quality, EMI interference, duplex mismatch)",
                    recommended_action="Inspect network cabling for damage or excessive length. Check for nearby sources of electromagnetic interference (motors, fluorescent lights). Verify duplex settings match on both ends.",
                    affected_isp=None,
                    technical_details={
                        "crc_errors": crc_errors,
                        "interface_status": "UP",
                        "diagnosis": "Physical layer degradation with link up"
                    }
                )

        # === DEFAULT: Everything looks normal ===
        return FaultAnalysis(
            fault_type=FaultType.UNDETERMINED,
            confidence=0.0,
            reason="Interface operational with no significant errors detected",
            recommended_action="No immediate action required. Continue monitoring interface metrics for changes.",
            affected_isp=None,
            technical_details={
                "device_status": device_ping_status,
                "interface_status": interface_oper_status,
                "in_errors": in_errors,
                "in_discards": in_discards,
                "crc_errors": crc_errors,
                "diagnosis": "Normal operation"
            }
        )

    @staticmethod
    def format_fault_message(analysis: FaultAnalysis, device_name: str, interface_name: str) -> str:
        """
        Format fault analysis into a human-readable alert message

        Args:
            analysis: FaultAnalysis result
            device_name: Name of the device
            interface_name: Name of the interface

        Returns:
            Formatted alert message string
        """
        fault_icon = {
            FaultType.CUSTOMER_SIDE: "🔧",
            FaultType.ISP_SIDE: "📡",
            FaultType.UNDETERMINED: "❓"
        }

        confidence_emoji = "🔴" if analysis.confidence > 0.8 else "🟡" if analysis.confidence > 0.5 else "⚪"

        message = f"""
{fault_icon.get(analysis.fault_type, '❓')} **FAULT CLASSIFICATION**

**Device:** {device_name}
**Interface:** {interface_name}
**ISP:** {analysis.affected_isp.upper() if analysis.affected_isp else 'N/A'}

{confidence_emoji} **Fault Type:** {analysis.fault_type.value.upper().replace('_', ' ')}
**Confidence:** {analysis.confidence * 100:.0f}%

📋 **Analysis:**
{analysis.reason}

💡 **Recommended Action:**
{analysis.recommended_action}
""".strip()

        return message


# Example usage for testing
if __name__ == "__main__":
    # Test Case 1: Device down
    print("=== Test Case 1: Device Down ===")
    result = ISPFaultClassifier.analyze_interface_fault(
        device_ping_status="Down",
        interface_oper_status="down",
        interface_admin_status="up",
        isp_name="magti"
    )
    print(ISPFaultClassifier.format_fault_message(result, "Branch Router 01", "Fa3"))
    print()

    # Test Case 2: High errors on ISP link
    print("=== Test Case 2: High ISP Errors ===")
    result = ISPFaultClassifier.analyze_interface_fault(
        device_ping_status="Up",
        interface_oper_status="up",
        interface_admin_status="up",
        in_errors=5000,
        in_octets=100_000_000,
        isp_name="silknet"
    )
    print(ISPFaultClassifier.format_fault_message(result, "Branch Router 02", "Fa4"))
    print()

    # Test Case 3: CRC errors (customer-side)
    print("=== Test Case 3: CRC Errors (Cable Issue) ===")
    result = ISPFaultClassifier.analyze_interface_fault(
        device_ping_status="Up",
        interface_oper_status="down",
        interface_admin_status="up",
        crc_errors=250,
        isp_name="magti"
    )
    print(ISPFaultClassifier.format_fault_message(result, "Branch Router 03", "Fa3"))
