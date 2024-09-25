from OpenSSL import crypto
from time import time
import os
import ssl


def generate_crt_and_key(hostname):
    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, 2048)

    crt = crypto.X509()
    subject = crt.get_subject()
    subject.commonName = hostname
    crt.set_issuer(subject)
    crt.gmtime_adj_notBefore(0)
    crt.gmtime_adj_notAfter(50 * 365 * 24 * 60 * 60)
    crt.set_pubkey(key)
    crt.set_serial_number(int(time()))
    crt.set_version(2)
    crt.sign(key, "SHA256")

    return crt, key


def wrap_socket(socket, crt_file, key_file, hostname=None):
    if not os.path.exists(crt_file) and not os.path.exists(key_file) and hostname is not None:
        crt, key = generate_crt_and_key(hostname)
        with open(crt_file, "wb") as f:
            f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, crt))
        with open(key_file, "wb") as f:
            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(crt_file, key_file)
    return context.wrap_socket(socket, server_side=True)


if __name__ == "__main__":
    data = "Hello world".encode("UTF-8")
    crt, key = generate_crt_and_key("test")
    signature = crypto.sign(key, data, "SHA256")
    ok = crypto.verify(crt, signature, data, "SHA256") is None
    print(signature.hex())
    print(ok)
