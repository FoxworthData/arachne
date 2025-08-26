import hashlib
import random
from dataclasses import dataclass
from typing import Dict


@dataclass
class BrowserPersona:
    """
    Browser persona with consistent fingerprinting data.
    """
    user_agent: str
    sec_ch_ua: str
    sec_ch_ua_mobile: str
    sec_ch_ua_platform: str
    device_specs: Dict[str, str]
    persona_id: str
    viewport_width: int
    viewport_height: int

    @classmethod
    def generate_persona_id(cls, user_agent: str) -> str:
        """Generate a unique persona ID based on user agent characteristics."""
        ua_hash = hashlib.md5(user_agent.encode()).hexdigest()[:8]

        if "Chrome" in user_agent and "Windows" in user_agent:
            return f"chrome-win-{ua_hash}"
        elif "Chrome" in user_agent and "Macintosh" in user_agent:
            return f"chrome-mac-{ua_hash}"
        elif "Chrome" in user_agent and "Linux" in user_agent:
            return f"chrome-linux-{ua_hash}"
        else:
            return f"unknown-{ua_hash}"


class BrowserPersonaChooser:
    """
    Browser persona management, contains curated Chrome personas for maximum bot evasion.

    Note: Only Chrome personas are used because Playwright only supports Chromium engines.
    Using Safari/Firefox personas with Chromium would create header/runtime mismatches
    that can be detected as bot behavior by anti-bot systems.
    """

    def __init__(self):
        # Curated Chrome personas only - compatible with Playwright's Chromium engine
        # Safari personas removed due to header/runtime mismatch causing bot detection
        self._personas_data = [
            # Chrome Windows - High success rate
            {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
                "sec_ch_ua": '"Google Chrome";v="137", "Chromium";v="137", "Not.A/Brand";v="24"',
                "sec_ch_ua_mobile": "?0",
                "sec_ch_ua_platform": '"Windows"',
                "device_specs": {
                    "downlink": "8.5",
                    "dpr": "1",
                    "rtt": "100",
                    "ect": "4g"
                },
                "viewport_width": 1920,
                "viewport_height": 1080
            },
            # Chrome macOS - High success rate
            {
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
                "sec_ch_ua": '"Google Chrome";v="137", "Chromium";v="137", "Not.A/Brand";v="24"',
                "sec_ch_ua_mobile": "?0",
                "sec_ch_ua_platform": '"macOS"',
                "device_specs": {
                    "downlink": "10.0",
                    "dpr": "2",
                    "rtt": "50",
                    "ect": "4g"
                },
                "viewport_width": 1440,
                "viewport_height": 900
            },
            # Chrome Linux - Added for additional variety while maintaining Chromium compatibility
            {
                "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
                "sec_ch_ua": '"Google Chrome";v="137", "Chromium";v="137", "Not.A/Brand";v="24"',
                "sec_ch_ua_mobile": "?0",
                "sec_ch_ua_platform": '"Linux"',
                "device_specs": {
                    "downlink": "9.2",
                    "dpr": "1",
                    "rtt": "75",
                    "ect": "4g"
                },
                "viewport_width": 1920,
                "viewport_height": 1080
            }
        ]

    def get_random_persona(self) -> BrowserPersona:
        """Select a random persona from curated list."""
        persona_data = random.choice(self._personas_data)
        persona_id = BrowserPersona.generate_persona_id(persona_data["user_agent"])

        return BrowserPersona(
            user_agent=persona_data["user_agent"],
            sec_ch_ua=persona_data["sec_ch_ua"],
            sec_ch_ua_mobile=persona_data["sec_ch_ua_mobile"],
            sec_ch_ua_platform=persona_data["sec_ch_ua_platform"],
            device_specs=persona_data["device_specs"],
            persona_id=persona_id,
            viewport_width=persona_data["viewport_width"],
            viewport_height=persona_data["viewport_height"]
        )

    def get_persona(self, os_name:str, browser_name:str) -> BrowserPersona:
        for persona_data in self._personas_data:
            if os_name in persona_data["user_agent"] and browser_name in persona_data["user_agent"]:
                persona_id = BrowserPersona.generate_persona_id(persona_data["user_agent"])

                return BrowserPersona(
                    user_agent=persona_data["user_agent"],
                    sec_ch_ua=persona_data["sec_ch_ua"],
                    sec_ch_ua_mobile=persona_data["sec_ch_ua_mobile"],
                    sec_ch_ua_platform=persona_data["sec_ch_ua_platform"],
                    device_specs=persona_data["device_specs"],
                    persona_id=persona_id,
                    viewport_width=persona_data["viewport_width"],
                    viewport_height=persona_data["viewport_height"]
                )

        return None