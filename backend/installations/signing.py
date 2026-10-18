"""Standard ES256 JWS; OCI holds private keys, installations hold public PEM keys."""
import base64
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path


def _encode_base64url(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def sign_licence(claims, *, key_id=None, key_version=None, endpoint=None):
    if not all((key_id, key_version, endpoint)):
        from django.conf import settings
        key_id = key_id or settings.OCI_LICENSE_KEY_ID
        key_version = key_version or settings.OCI_LICENSE_KEY_VERSION
        endpoint = endpoint or settings.OCI_SIGNING_ENDPOINT
    import oci
    from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
    signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
    client = oci.key_management.KmsCryptoClient({}, signer=signer, service_endpoint=endpoint,
        timeout=(4, 12), retry_strategy=oci.retry.NoneRetryStrategy())
    kid = key_version
    header = _encode_base64url(json.dumps({"alg": "ES256", "typ": "JWT", "kid": kid}, separators=(",", ":")).encode())
    payload = _encode_base64url(json.dumps(claims, separators=(",", ":"), sort_keys=True).encode())
    message = f"{header}.{payload}"
    details = oci.key_management.models.SignDataDetails(key_id=key_id, key_version_id=kid,
        signing_algorithm="ECDSA_SHA_256", message_type="DIGEST", message=base64.b64encode(hashlib.sha256(message.encode()).digest()).decode())
    der = base64.b64decode(client.sign(details).data.signature)
    r, s = decode_dss_signature(der)
    return message + "." + _encode_base64url(r.to_bytes(32, "big") + s.to_bytes(32, "big"))


def verify_licence(token, installation_id, *, now=None):
    from django.conf import settings
    import jwt
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicKey, SECP256R1
    if not isinstance(token, str) or len(token) > 32768:
        raise ValueError("Invalid licence size")
    header = jwt.get_unverified_header(token)
    if header.get("alg") != "ES256" or not isinstance(header.get("kid"), str):
        raise ValueError("Unsupported licence algorithm/key")
    keys = json.loads(Path(settings.LICENSE_PUBLIC_KEYS_FILE).read_text(encoding="utf-8"))
    pem = keys.get(header["kid"])
    if not pem:
        raise ValueError("Unknown licence verification key")
    key = load_pem_public_key(pem.encode())
    if not isinstance(key, EllipticCurvePublicKey) or not isinstance(key.curve, SECP256R1):
        raise ValueError("Licence verification requires P-256")
    claims = jwt.decode(token, key, algorithms=["ES256"], issuer="quantnest-licensing", audience=str(installation_id),
        options={"verify_exp": False, "require": ["schema_version", "iss", "aud", "iat", "exp", "revision", "paid_through", "qualified_integrations", "live_approved_until"]})
    if type(claims["schema_version"]) is not int or claims["schema_version"] != 3:
        raise ValueError("Refresh the installation licence for the current allowance schema")
    clock = int((now or datetime.now(timezone.utc)).timestamp())
    for name in ("iat", "exp", "revision", "paid_through", "live_approved_until"):
        if type(claims[name]) is not int:
            raise ValueError("Licence timestamps and revisions must be integers")
    if claims["iat"] > clock + 120 or claims["exp"] <= claims["iat"] or claims["revision"] < 1:
        raise ValueError("Invalid licence issue/revision interval")
    if claims["exp"] > claims["paid_through"] or (not claims.get("offline") and claims["exp"] - claims["iat"] > 24 * 3600):
        raise ValueError("Licence exceeds its approved lease")
    if not isinstance(claims["qualified_integrations"], list) or any(not isinstance(value, str) for value in claims["qualified_integrations"]):
        raise ValueError("Invalid qualified integrations")
    return claims
