"""Canadian recognizers for Microsoft Presidio."""

from canpii.recognizers._base import CanadianPatternRecognizer
from canpii.recognizers.ca_ab_phn_recognizer import CaAbPhnRecognizer
from canpii.recognizers.ca_bank_account_recognizer import CaBankAccountRecognizer
from canpii.recognizers.ca_bc_driver_license_recognizer import (
    CaBcDriverLicenseRecognizer,
)
from canpii.recognizers.ca_bc_phn_recognizer import CaBcPhnRecognizer
from canpii.recognizers.ca_business_number_recognizer import (
    CaBusinessNumberRecognizer,
)
from canpii.recognizers.ca_on_driver_license_recognizer import (
    CaOnDriverLicenseRecognizer,
)
from canpii.recognizers.ca_on_ohip_recognizer import CaOnOhipRecognizer
from canpii.recognizers.ca_passport_recognizer import CaPassportRecognizer
from canpii.recognizers.ca_qc_driver_license_recognizer import (
    CaQcDriverLicenseRecognizer,
)
from canpii.recognizers.ca_qc_ramq_recognizer import CaQcRamqRecognizer

#: Every recognizer class shipped by this package, in documentation order.
ALL_RECOGNIZERS: tuple[type[CanadianPatternRecognizer], ...] = (
    CaOnOhipRecognizer,
    CaQcRamqRecognizer,
    CaBcPhnRecognizer,
    CaAbPhnRecognizer,
    CaPassportRecognizer,
    CaBusinessNumberRecognizer,
    CaBankAccountRecognizer,
    CaOnDriverLicenseRecognizer,
    CaQcDriverLicenseRecognizer,
    CaBcDriverLicenseRecognizer,
)

__all__ = [
    "ALL_RECOGNIZERS",
    "CaAbPhnRecognizer",
    "CaBankAccountRecognizer",
    "CaBcDriverLicenseRecognizer",
    "CaBcPhnRecognizer",
    "CaBusinessNumberRecognizer",
    "CaOnDriverLicenseRecognizer",
    "CaOnOhipRecognizer",
    "CaPassportRecognizer",
    "CaQcDriverLicenseRecognizer",
    "CaQcRamqRecognizer",
    "CanadianPatternRecognizer",
]
