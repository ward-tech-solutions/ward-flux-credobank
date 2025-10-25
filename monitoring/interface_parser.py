"""
WARD FLUX - Interface Parser
Classifies network interfaces based on descriptions and names
Extracts ISP provider, interface type, and criticality
"""

import re
import logging
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class InterfaceClassification:
    """Result of interface classification"""
    interface_type: str  # isp, trunk, access, server_link, branch_link, management, other
    isp_provider: Optional[str] = None  # magti, silknet, veon, beeline, geocell
    is_critical: bool = False
    confidence: float = 0.0  # 0.0 to 1.0
    matched_pattern: Optional[str] = None


class InterfaceParser:
    """
    Parse and classify network interface descriptions

    Handles various naming conventions:
    - ISP interfaces: "Magti_Internet", "internet_magti", "INTERNET-MAGTI", "ISP Magti"
    - Trunk ports: "Trunk_to_CoreSwitch", "Po1", "LAG1", "Trunk-Link"
    - Server links: "Server_Connection_01", "SRV-HOST", "ESXi-1"
    - Branch links: "Branch_Rustavi", "VPN_Tunnel", "To_Branch_Office"
    - Management: "Management", "MGMT", "Admin"
    - Access: "Access", "User", "Employee"
    """

    # ISP providers in Georgia
    ISP_PROVIDERS = {
        'magti': ['magti', 'magticom', 'magtico'],
        'silknet': ['silknet', 'silk', 'silkn'],
        'veon': ['veon', 'beeline', 'bline'],
        'beeline': ['veon', 'beeline', 'bline'],  # Beeline rebranded to Veon
        'geocell': ['geocell', 'geo', 'gcell'],
        'caucasus': ['caucasus', 'con', 'caucasus_online'],
        'globaltel': ['globaltel', 'global'],
    }

    # Interface type patterns (order matters - more specific first)
    INTERFACE_PATTERNS = {
        'isp': [
            # ISP + keywords
            r'(?i)(magti|silknet|veon|beeline|geocell|caucasus|globaltel)[\s_-]*(internet|inet|wan|uplink|isp|bgp)',
            r'(?i)(internet|inet|wan|uplink|isp|bgp)[\s_-]*(magti|silknet|veon|beeline|geocell|caucasus|globaltel)',

            # Generic ISP/WAN indicators
            r'(?i)isp[\s_-]*\d*',
            r'(?i)wan[\s_-]*\d*',
            r'(?i)(internet|inet)[\s_-]*(uplink|link|connection)',
            r'(?i)bgp[\s_-]*(peer|neighbor|uplink)',
            r'(?i)upstream[\s_-]*\d*',
            r'(?i)provider[\s_-]*\d*',
        ],

        'trunk': [
            # Explicit trunk naming
            r'(?i)trunk[\s_-]*(to|link)?[\s_-]*\w*',
            r'(?i)trnk[\s_-]*\w*',

            # Port-channel / LAG
            r'(?i)po\d+',  # Po1, Po2, etc.
            r'(?i)port[\s_-]*channel[\s_-]*\d+',
            r'(?i)lag\d+',  # LAG1, LAG2
            r'(?i)link[\s_-]*aggregation[\s_-]*\d+',

            # Core/backbone links
            r'(?i)core[\s_-]*(link|uplink|switch)',
            r'(?i)backbone',
            r'(?i)aggregation[\s_-]*(switch|layer)',
        ],

        'server_link': [
            # Server connections
            r'(?i)server[\s_-]*(connection|link|port|host)',
            r'(?i)srv[\s_-]*(host|conn|link)',

            # Hypervisors
            r'(?i)(esxi|vcenter|vmware|hyper-v)[\s_-]*\d*',
            r'(?i)vm[\s_-]*host[\s_-]*\d*',

            # Application servers
            r'(?i)(web|app|database|db|sql)[\s_-]*server',
            r'(?i)(storage|nas|san)[\s_-]*(link|connection)',
        ],

        'branch_link': [
            # Branch offices
            r'(?i)branch[\s_-]*(office|link|connection)?[\s_-]*\w*',

            # VPN tunnels
            r'(?i)vpn[\s_-]*(tunnel|connection|link)',
            r'(?i)tunnel[\s_-]*\d*',

            # Remote sites
            r'(?i)(remote|site)[\s_-]*(office|link|connection)',
            r'(?i)to[\s_-]*\w+[\s_-]*(branch|office|site)',

            # Georgian cities (common branch locations)
            r'(?i)(rustavi|kutaisi|batumi|zugdidi|telavi|gori|mtskheta|poti|kobuleti|marneuli|gardabani|borjomi)[\s_-]*(branch|office|link)?',
        ],

        'management': [
            # Management interfaces
            r'(?i)management',
            r'(?i)mgmt',
            r'(?i)admin',
            r'(?i)control[\s_-]*plane',
        ],

        'access': [
            # Access ports
            r'(?i)access[\s_-]*(port|switch|vlan)',
            r'(?i)user[\s_-]*(port|access)',
            r'(?i)employee[\s_-]*(port|access)',
            r'(?i)desktop[\s_-]*(port|access)',
        ],

        'loopback': [
            # Loopback interfaces
            r'(?i)loopback[\s_-]*\d*',
            r'(?i)lo\d+',
        ],

        'voice': [
            # Voice/VoIP
            r'(?i)voice[\s_-]*(vlan|port)',
            r'(?i)voip',
            r'(?i)phone[\s_-]*(port|vlan)',
        ],

        'camera': [
            # CCTV/IP cameras
            r'(?i)(camera|cctv|nvr|ipcam)[\s_-]*\d*',
            r'(?i)surveillance',
        ],
    }

    def __init__(self):
        """Initialize the interface parser"""
        # Compile regex patterns for performance
        self.compiled_patterns: Dict[str, List[re.Pattern]] = {}
        for interface_type, patterns in self.INTERFACE_PATTERNS.items():
            self.compiled_patterns[interface_type] = [
                re.compile(pattern) for pattern in patterns
            ]

    def classify_interface(
        self,
        if_alias: Optional[str] = None,
        if_descr: Optional[str] = None,
        if_name: Optional[str] = None,
        if_type: Optional[str] = None
    ) -> InterfaceClassification:
        """
        Classify an interface based on available information

        Args:
            if_alias: ifAlias - user-configured description (MOST IMPORTANT)
            if_descr: ifDescr - system description
            if_name: ifName - interface name (Gi0/0/0, etc.)
            if_type: ifType - interface type (ethernet, tunnel, etc.)

        Returns:
            InterfaceClassification with type, ISP provider, criticality, and confidence
        """

        # Combine all available text (prioritize if_alias)
        text_to_parse = []
        if if_alias:
            text_to_parse.append(('if_alias', if_alias, 1.0))  # Highest priority
        if if_descr:
            text_to_parse.append(('if_descr', if_descr, 0.7))  # Medium priority
        if if_name:
            text_to_parse.append(('if_name', if_name, 0.5))    # Lower priority

        if not text_to_parse:
            return InterfaceClassification(
                interface_type='other',
                confidence=0.0
            )

        # Try to classify based on each text field
        best_classification = None
        best_confidence = 0.0

        for source, text, weight in text_to_parse:
            classification = self._classify_text(text, if_type)

            # Adjust confidence based on source weight
            weighted_confidence = classification.confidence * weight

            if weighted_confidence > best_confidence:
                best_confidence = weighted_confidence
                best_classification = classification

        # Update confidence to weighted value
        if best_classification:
            best_classification.confidence = best_confidence

        # Extract ISP provider if interface type is ISP
        if best_classification and best_classification.interface_type == 'isp':
            isp_provider = self._extract_isp_provider(if_alias, if_descr, if_name)
            best_classification.isp_provider = isp_provider

            # ISP interfaces are critical
            best_classification.is_critical = True

        return best_classification or InterfaceClassification(
            interface_type='other',
            confidence=0.0
        )

    def _classify_text(self, text: str, if_type: Optional[str] = None) -> InterfaceClassification:
        """
        Classify interface based on a single text field

        Args:
            text: Text to classify (description, alias, or name)
            if_type: Interface type from SNMP (optional)

        Returns:
            InterfaceClassification
        """
        if not text:
            return InterfaceClassification(interface_type='other', confidence=0.0)

        text = text.strip()

        # Special case: Loopback interfaces
        if if_type and 'loopback' in if_type.lower():
            return InterfaceClassification(
                interface_type='loopback',
                confidence=1.0,
                matched_pattern='ifType=loopback'
            )

        # Try to match against all patterns (order matters)
        for interface_type, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    # Calculate confidence based on match quality
                    confidence = self._calculate_confidence(text, match)

                    return InterfaceClassification(
                        interface_type=interface_type,
                        confidence=confidence,
                        matched_pattern=pattern.pattern
                    )

        # No pattern matched - classify as "other"
        return InterfaceClassification(
            interface_type='other',
            confidence=0.5
        )

    def _calculate_confidence(self, text: str, match: re.Match) -> float:
        """
        Calculate confidence score for a pattern match

        Higher confidence when:
        - Match covers more of the text
        - Match is at the beginning of text
        - Multiple keywords present

        Args:
            text: Original text
            match: Regex match object

        Returns:
            Confidence score (0.0 to 1.0)
        """
        confidence = 0.7  # Base confidence

        # Boost if match is at the beginning
        if match.start() == 0:
            confidence += 0.1

        # Boost based on match coverage
        match_coverage = len(match.group(0)) / len(text)
        confidence += match_coverage * 0.2

        # Cap at 1.0
        return min(confidence, 1.0)

    def _extract_isp_provider(
        self,
        if_alias: Optional[str] = None,
        if_descr: Optional[str] = None,
        if_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Extract ISP provider name from interface description

        Args:
            if_alias: Interface alias
            if_descr: Interface description
            if_name: Interface name

        Returns:
            ISP provider name (normalized) or None
        """
        # Combine all text
        text = ' '.join(filter(None, [if_alias, if_descr, if_name])).lower()

        # Check for each ISP provider
        for provider, aliases in self.ISP_PROVIDERS.items():
            for alias in aliases:
                if alias.lower() in text:
                    return provider  # Return normalized name

        return None

    def is_critical_interface(
        self,
        interface_type: str,
        isp_provider: Optional[str] = None,
        if_alias: Optional[str] = None
    ) -> bool:
        """
        Determine if an interface is critical for monitoring

        Critical interfaces:
        - All ISP uplinks
        - Core/backbone trunks
        - Primary server connections (if marked as "primary" or "prod")

        Args:
            interface_type: Classified interface type
            isp_provider: ISP provider (if applicable)
            if_alias: Interface alias for additional checks

        Returns:
            True if interface is critical
        """
        # All ISP interfaces are critical
        if interface_type == 'isp':
            return True

        # Trunk interfaces to core/backbone are critical
        if interface_type == 'trunk' and if_alias:
            alias_lower = if_alias.lower()
            critical_keywords = ['core', 'backbone', 'aggregation', 'primary', 'main']
            if any(keyword in alias_lower for keyword in critical_keywords):
                return True

        # Server links marked as production are critical
        if interface_type == 'server_link' and if_alias:
            alias_lower = if_alias.lower()
            critical_keywords = ['prod', 'production', 'primary', 'critical']
            if any(keyword in alias_lower for keyword in critical_keywords):
                return True

        return False

    def parse_batch(
        self,
        interfaces: List[Dict[str, any]]
    ) -> List[Tuple[Dict[str, any], InterfaceClassification]]:
        """
        Parse a batch of interfaces

        Args:
            interfaces: List of interface dicts with keys:
                       if_index, if_name, if_descr, if_alias, if_type

        Returns:
            List of tuples (interface_dict, classification)
        """
        results = []

        for interface in interfaces:
            classification = self.classify_interface(
                if_alias=interface.get('if_alias'),
                if_descr=interface.get('if_descr'),
                if_name=interface.get('if_name'),
                if_type=interface.get('if_type')
            )

            results.append((interface, classification))

        return results


# Global parser instance (singleton)
interface_parser = InterfaceParser()


# Convenience functions for direct usage
def classify_interface(
    if_alias: Optional[str] = None,
    if_descr: Optional[str] = None,
    if_name: Optional[str] = None,
    if_type: Optional[str] = None
) -> InterfaceClassification:
    """Convenience function to classify an interface"""
    return interface_parser.classify_interface(if_alias, if_descr, if_name, if_type)


def is_critical_interface(
    interface_type: str,
    isp_provider: Optional[str] = None,
    if_alias: Optional[str] = None
) -> bool:
    """Convenience function to check if interface is critical"""
    return interface_parser.is_critical_interface(interface_type, isp_provider, if_alias)
