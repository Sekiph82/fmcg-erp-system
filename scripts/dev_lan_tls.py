"""LOCAL development only: a tiny certificate authority for testing the app on a phone over HTTPS on the Wi-Fi.

Creates .lan-tls/ (never committed):
  rootCA.crt / rootCA.key  - the test CA. It is NAME-CONSTRAINED to the given LAN address only, so even if it stays
                             installed on the phone it cannot vouch for any other site (bank, Google, ...).
  lan.crt / lan.key        - the server certificate for https://<LAN_IP> used by the Caddy proxy.
Remove the profile from the phone after testing (Settings > General > VPN & Device Management).

Usage:  python scripts/dev_lan_tls.py 192.168.1.189
"""
import datetime as dt
import ipaddress
import pathlib
import sys

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

ip = ipaddress.ip_address(sys.argv[1])
out = pathlib.Path(__file__).resolve().parents[1] / ".lan-tls"
out.mkdir(exist_ok=True)
now = dt.datetime.now(dt.timezone.utc)


def key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def save(name, obj, private=False):
    data = (obj.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL,
                              serialization.NoEncryption()) if private else obj.public_bytes(serialization.Encoding.PEM))
    (out / name).write_bytes(data)


ca_key = key()
ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, f"FMCG ERP local test CA ({ip} only)"),
                     x509.NameAttribute(NameOID.ORGANIZATION_NAME, "FMCG ERP development")])
ca = (x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name).public_key(ca_key.public_key())
      .serial_number(x509.random_serial_number()).not_valid_before(now - dt.timedelta(minutes=5))
      .not_valid_after(now + dt.timedelta(days=90))
      .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
      .add_extension(x509.KeyUsage(digital_signature=True, key_cert_sign=True, crl_sign=True, content_commitment=False,
                                   key_encipherment=False, data_encipherment=False, key_agreement=False,
                                   encipher_only=False, decipher_only=False), critical=True)
      # the CA may only sign certificates for this one LAN address
      .add_extension(x509.NameConstraints(permitted_subtrees=[x509.IPAddress(ipaddress.ip_network(f"{ip}/32"))],
                                          excluded_subtrees=None), critical=True)
      .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
      .sign(ca_key, hashes.SHA256()))

leaf_key = key()
leaf = (x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, str(ip))]))
        .issuer_name(ca_name).public_key(leaf_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(minutes=5)).not_valid_after(now + dt.timedelta(days=90))
        .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ip)]), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
        .sign(ca_key, hashes.SHA256()))

save("rootCA.crt", ca)
save("rootCA.key", ca_key, private=True)
save("lan.crt", leaf)
save("lan.key", leaf_key, private=True)
print(f"Created {out} for {ip} (valid 90 days)")
