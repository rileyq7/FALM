#!/usr/bin/env python3
"""
Automatic Funding Body Detection
Analyzes URLs and content to determine the correct funding body and silo
"""

from typing import Tuple, Optional
import re

class FundingBodyDetector:
    """Automatically detect funding body from URL and content"""

    # UK Funding Bodies
    UK_BODIES = {
        "IUK": {
            "name": "Innovate UK",
            "patterns": [
                r"innovate.*uk",
                r"apply-for-innovation-funding",
                r"ktn-uk",
                r"catapult"
            ],
            "domains": [
                "apply-for-innovation-funding.service.gov.uk",
                "ktn-uk.org",
                "catapult.org.uk"
            ]
        },
        "NIHR": {
            "name": "National Institute for Health Research",
            "patterns": [
                r"nihr",
                r"national institute.*health research"
            ],
            "domains": [
                "nihr.ac.uk"
            ]
        },
        "UKRI": {
            "name": "UK Research and Innovation",
            "patterns": [
                r"ukri",
                r"uk research.*innovation"
            ],
            "domains": [
                "ukri.org"
            ]
        },
        "EPSRC": {
            "name": "Engineering and Physical Sciences Research Council",
            "patterns": [
                r"epsrc",
                r"engineering.*physical sciences"
            ],
            "domains": [
                "epsrc.ukri.org"
            ]
        },
        "ESRC": {
            "name": "Economic and Social Research Council",
            "patterns": [
                r"esrc",
                r"economic.*social research"
            ],
            "domains": [
                "esrc.ukri.org"
            ]
        },
        "MRC": {
            "name": "Medical Research Council",
            "patterns": [
                r"\bmrc\b",
                r"medical research council"
            ],
            "domains": [
                "mrc.ukri.org"
            ]
        },
        "NERC": {
            "name": "Natural Environment Research Council",
            "patterns": [
                r"nerc",
                r"natural environment research"
            ],
            "domains": [
                "nerc.ukri.org"
            ]
        },
        "AHRC": {
            "name": "Arts and Humanities Research Council",
            "patterns": [
                r"ahrc",
                r"arts.*humanities research"
            ],
            "domains": [
                "ahrc.ukri.org"
            ]
        },
        "BBSRC": {
            "name": "Biotechnology and Biological Sciences Research Council",
            "patterns": [
                r"bbsrc",
                r"biotechnology.*biological"
            ],
            "domains": [
                "bbsrc.ukri.org"
            ]
        },
        "STFC": {
            "name": "Science and Technology Facilities Council",
            "patterns": [
                r"stfc",
                r"science.*technology facilities"
            ],
            "domains": [
                "stfc.ukri.org"
            ]
        },
        "Wellcome": {
            "name": "Wellcome Trust",
            "patterns": [
                r"wellcome"
            ],
            "domains": [
                "wellcome.org",
                "wellcome.ac.uk"
            ]
        },
        "CRUK": {
            "name": "Cancer Research UK",
            "patterns": [
                r"cancer research uk",
                r"cruk"
            ],
            "domains": [
                "cancerresearchuk.org"
            ]
        },
        "BHF": {
            "name": "British Heart Foundation",
            "patterns": [
                r"british heart foundation",
                r"\bbhf\b"
            ],
            "domains": [
                "bhf.org.uk"
            ]
        },
        "ACE": {
            "name": "Arts Council England",
            "patterns": [
                r"arts council england",
                r"arts council"
            ],
            "domains": [
                "artscouncil.org.uk"
            ]
        }
    }

    # EU Funding Bodies
    EU_BODIES = {
        "EIC": {
            "name": "European Innovation Council",
            "patterns": [
                r"\beic\b",
                r"european innovation council"
            ],
            "domains": [
                "eic.ec.europa.eu"
            ]
        },
        "Horizon": {
            "name": "Horizon Europe",
            "patterns": [
                r"horizon europe",
                r"horizon 2020"
            ],
            "domains": [
                "ec.europa.eu/info/funding-tenders"
            ]
        },
        "EIT": {
            "name": "European Institute of Innovation and Technology",
            "patterns": [
                r"\beit\b",
                r"european institute.*innovation"
            ],
            "domains": [
                "eit.europa.eu"
            ]
        },
        "LIFE": {
            "name": "LIFE Programme",
            "patterns": [
                r"life programme",
                r"life climate",
                r"cinea"
            ],
            "domains": [
                "cinea.ec.europa.eu/programmes/life"
            ]
        }
    }

    # US Funding Bodies
    US_BODIES = {
        "NSF": {
            "name": "National Science Foundation",
            "patterns": [
                r"\bnsf\b",
                r"national science foundation",
                r"sbir",
                r"sttr"
            ],
            "domains": [
                "nsf.gov",
                "seedfund.nsf.gov"
            ]
        },
        "NIH": {
            "name": "National Institutes of Health",
            "patterns": [
                r"\bnih\b",
                r"national institutes.*health"
            ],
            "domains": [
                "nih.gov",
                "grants.nih.gov"
            ]
        },
        "DOE": {
            "name": "Department of Energy",
            "patterns": [
                r"\bdoe\b",
                r"department.*energy",
                r"arpa-e"
            ],
            "domains": [
                "energy.gov",
                "arpa-e.energy.gov"
            ]
        },
        "DOD": {
            "name": "Department of Defense",
            "patterns": [
                r"\bdod\b",
                r"department.*defense",
                r"darpa"
            ],
            "domains": [
                "defense.gov",
                "darpa.mil"
            ]
        },
        "NASA": {
            "name": "NASA",
            "patterns": [
                r"nasa",
                r"space.*administration"
            ],
            "domains": [
                "nasa.gov"
            ]
        }
    }

    @classmethod
    def detect_from_url(cls, url: str) -> Tuple[str, str, str]:
        """
        Detect funding body from URL
        Returns: (silo, funding_body_code, funding_body_name)
        """
        url_lower = url.lower()

        # Check UK
        for code, info in cls.UK_BODIES.items():
            for domain in info["domains"]:
                if domain in url_lower:
                    return "UK", code, info["name"]
            for pattern in info["patterns"]:
                if re.search(pattern, url_lower, re.IGNORECASE):
                    return "UK", code, info["name"]

        # Check EU
        for code, info in cls.EU_BODIES.items():
            for domain in info["domains"]:
                if domain in url_lower:
                    return "EU", code, info["name"]
            for pattern in info["patterns"]:
                if re.search(pattern, url_lower, re.IGNORECASE):
                    return "EU", code, info["name"]

        # Check US
        for code, info in cls.US_BODIES.items():
            for domain in info["domains"]:
                if domain in url_lower:
                    return "US", code, info["name"]
            for pattern in info["patterns"]:
                if re.search(pattern, url_lower, re.IGNORECASE):
                    return "US", code, info["name"]

        # Default
        return "UK", "Unknown", "Unknown Provider"

    @classmethod
    def detect_from_content(cls, text: str, url: str = "") -> Tuple[str, str, str]:
        """
        Detect funding body from page content and URL
        Returns: (silo, funding_body_code, funding_body_name)
        """
        # First try URL
        if url:
            result = cls.detect_from_url(url)
            if result[1] != "Unknown":
                return result

        # Then try content
        text_lower = text.lower()

        # Check UK
        for code, info in cls.UK_BODIES.items():
            for pattern in info["patterns"]:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    return "UK", code, info["name"]

        # Check EU
        for code, info in cls.EU_BODIES.items():
            for pattern in info["patterns"]:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    return "EU", code, info["name"]

        # Check US
        for code, info in cls.US_BODIES.items():
            for pattern in info["patterns"]:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    return "US", code, info["name"]

        # Default
        return "UK", "Unknown", "Unknown Provider"

    @classmethod
    def get_all_bodies(cls) -> dict:
        """Get all funding bodies organized by silo"""
        return {
            "UK": cls.UK_BODIES,
            "EU": cls.EU_BODIES,
            "US": cls.US_BODIES
        }


def test_detector():
    """Test the funding body detector"""
    test_urls = [
        "https://apply-for-innovation-funding.service.gov.uk/competition/2313/overview",
        "https://www.nihr.ac.uk/explore-nihr/funding-programmes/",
        "https://www.ukri.org/opportunity/",
        "https://epsrc.ukri.org/funding/",
        "https://wellcome.org/grant-funding/",
        "https://eic.ec.europa.eu/eic-funding-opportunities_en",
        "https://seedfund.nsf.gov/",
        "https://www.nih.gov/grants-funding",
    ]

    print("Testing Funding Body Detection:")
    print("=" * 60)

    for url in test_urls:
        silo, code, name = FundingBodyDetector.detect_from_url(url)
        print(f"\nURL: {url}")
        print(f"  Silo: {silo}")
        print(f"  Code: {code}")
        print(f"  Name: {name}")


if __name__ == "__main__":
    test_detector()
