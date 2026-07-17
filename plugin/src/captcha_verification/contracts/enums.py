from __future__ import annotations

from enum import Enum


class FactLevel(str, Enum):
    OBSERVED = "observed"
    DERIVED = "derived"
    ASSUMED = "assumed"
    UNVERIFIED = "unverified"


class OperationStatus(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"


class PredictionStatus(str, Enum):
    NOT_RUN = "not_run"
    PRODUCED = "produced"
    LOW_CONFIDENCE = "low_confidence"
    UNSUPPORTED = "unsupported"
    FAILED = "failed"


class ExecutionStatus(str, Enum):
    NOT_RUN = "not_run"
    COMPLETED = "completed"
    REJECTED = "rejected"
    ERRORED = "errored"


class ProviderVerificationStatus(str, Enum):
    NOT_ATTEMPTED = "not_attempted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    BOUNDARY_ONLY = "boundary_only"


class BusinessAcceptanceStatus(str, Enum):
    NOT_ATTEMPTED = "not_attempted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    INCONSISTENT = "inconsistent"


class PromotionStatus(str, Enum):
    INELIGIBLE = "ineligible"
    NEGATIVE_ONLY = "negative_only"
    CANDIDATE = "candidate"
    APPROVED = "approved"


class AuthorizationBasis(str, Enum):
    OWNED = "owned"
    WRITTEN_CONTRACT = "written_contract"
    TICKET = "ticket"
    CUSTOMER_CONTROLLED_INTEGRATION = "customer_controlled_integration"
    ORAL_CLAIM = "oral_claim"


class AuthorizationStatus(str, Enum):
    CLAIMED_UNVERIFIED = "claimed_unverified"
    VERIFIED = "verified"
    EXPIRED = "expired"
    REVOKED = "revoked"
    REJECTED = "rejected"


class ChallengeFamily(str, Enum):
    UNKNOWN = "unknown"
    SLIDER = "slider"
    ROTATE = "rotate"
    CLICK = "click"


class CaptureSpace(str, Enum):
    INTRINSIC_IMAGE_PX = "intrinsic_image_px"
    SCREENSHOT_DEVICE_PX = "screenshot_device_px"


class ReceiptKind(str, Enum):
    LOCAL_EXECUTION = "local_execution_receipt"
    PROVIDER = "provider_receipt"
    BUSINESS = "business_receipt"


class SolutionType(str, Enum):
    TEXT = "text"
    POINTS = "points"
    TILES = "tiles"
    OFFSET = "offset"
    ANGLE = "angle"
    TRACK = "track"
    PRESS = "press"


class ActionKind(str, Enum):
    POINTER_DOWN = "pointer_down"
    POINTER_MOVE = "pointer_move"
    POINTER_UP = "pointer_up"
    TAP = "tap"
    CLICK = "click"
    WAIT = "wait"
    TYPE_TEXT = "type_text"
    PRESS = "press"
    ROTATE = "rotate"
