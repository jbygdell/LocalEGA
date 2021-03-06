Keyserver
=========

The keyserver either returns a application-locked key or the currently
active key. If the ``Content-Type: text/plain`` is requested, the
ASCII-armored key is returned, otherwise the binary format is
returned. The components requesting the keys should have the
application token/password in order to unlock the received keys. In
case the request is unsuccessful the response code is ``404``.

**Active key endpoint**:

* ``/active/private`` - GET request for the private part of the active key
* ``/active/public`` - GET request for the public part of the active key

**Retrieve keys endpoint**:

* ``/retrieve/<key_id>/private`` - GET request for a private PGP key with a given ``<key_id>`` of fingerprint
* ``/retrieve/<key_id>/public`` - GET request for a public PGP key with a given ``<key_id>`` of fingerprint

**Admin endpoint**:

* ``/admin/unlock`` - POST request to unlock a key with a known path
* ``/admin/ttl`` - GET request to check when keys will expire

**Health endpoint**: ``/health`` will answer with ``200``


For example, sending a request (with ``Content-Type: text/plain``
header) to the ``/active/public`` endpoint:

.. sourcecode:: http

  GET /active/public HTTP/1.1
  Host: localhost:8443
  Accept: */*
  Content-Type: text/plain

gives the following response.

.. sourcecode:: http

  HTTP/1.1 200 OK
  Content-Length: 1632
  Content-Type: text/plain; charset=utf-8
  Body:   -----BEGIN PGP PUBLIC KEY BLOCK-----
          Version: PGPy v0.4.3

          xsFNBFsn1IsBEADkzI/sB/Ngr8NZ3YOtCvVRg5rfEFOlz0d2cb6Pfb3gZVpLuUW8
          EkfZfZIzkWd6DN9hRo+O/dWaplA3g8h9fp1yzUPQL8C8k1Uq+Lj7dGPsa/rPdp2x
          j+JzN31OPYtbRFL4wuj8CpXLvmGbIddnoX8jtd3AJ/07KPsQSlfnRX9xq7/vLDSL
          4A8sTiSum7zEvFIbKL9uWXD28Oos3HGGACSThDusDao31EoTjnTpar9mXWZL/r6H
          43naosDC8zmmMdQXIIuI95qfBmzKsIvqF+cvybSOwuFRSzz0T0yVe9dIO2y4Wdsk
          jfBSETosg+55A4xdL/APWjNJg6NxPvrZjkGiWXBfip4d95J63jbRMYcbBSBneIS+
          AvncOdLvKPQlUsz0URxRMOsnBMrt21g1JlO/QMikS5s0v5b2Gk2JxdF436cCQj2G
          iMZr5oFBbTHA8Se0lCqLeo4iAQweDFkkGbMgCEntPsuuBmXn7oCEee7P3DpFYY0W
          Up5Voh9A/j148xQkyH6OrpmbnW6PRhkCu0nnpPta4+WoBD17mBMIBiigrGXW7cDn
          fH/NR+M2HbijzS80l1prPzYtRIoKVRk5BmNoob6YufFILY5wDtDbEuIB7akL5vP7
          0eR6Kx0B7nNUKfyQMI4uN1JMuhfs39mPnhR87/e4840oB4HebLqkPuVjTwARAQAB
          zSNMb2NhbEVHQSAoQGxlZ2EpIDxsb2NhbC1lZ2FAZWdhLmV1PsLBcwQTAQgAHQUC
          WyfUjAIbDgQLCQgHBRUICQoLBRYCAwEAAh4BAAoJEHDl7bmyVEhR9moP/jIuFRLU
          LguKqzj5mEU1LV7ZabW3Gmahq92YJIZ2YreFWkMalOQbjDfZh92249Q2LdkcY+sA
          C9IdNG56oLaPqVcNskWmBHy3JvrYEMdoIzU0fk0EGP4iklHtDOp2IKfc1C+/HIzM
          tzrQbPpzjg+IcSmD7W3Oc2tPifat0VRQDbjB1jPnV4lKLO/BBxgKgiOi6hPiURNW
          5Ir1Ak7FXK+KEJ4XBFISBhcWjhAEXqIVmiemAjC2xQY6S0veao9A8rh05Xrs+Hum
          cJKdcoTOMWjm38qQsn390HmKTqPSVQsmrRwXgd5cfd9TD0ZWOk3g5f0O1IxfV3P5
          Y88LaVSsCypP7wFEYMFttNkBHR9ZHYWQTVLEtp7he3xTIczN/XZLvz0+dhGAwmFI
          zyVrtZFYiWuLnE1C0/dP1cwj8M9UepISTplVbEI+E1zDrnRealvZ3m+comwKkiV6
          +OXKzDpMH0/w4Yd9mMgFQUTaZ3haOvf+LXX4QCLolcz+BTLUvrxaEUzeS12mg91w
          0x7nXVukuIeHyRPAQtAneg/b/cjBWn5HqP6j+8TanFXNuedKj15/d8uehsfCQX7F
          6+6i915NEW1Nt3KU4pcVr+FVa44CzyNpK1YZ5WKujDpSwWOFj+qqoLHRUGHez8XF
          cr0SLPSsoG4Sld22f2x0JWpZIBN96h1oUxr6
          =IFAc
          -----END PGP PUBLIC KEY BLOCK-----

Generating PGP Key Pair
-----------------------

For convenience we have provided a `script <https://github.com/NBISweden/LocalEGA/blob/dev/extras/generate_pgp_key.py>`_ for generating a PGP key pair based on `PGPy <https://pgpy.readthedocs.io>`_ .
We make use of the script in :ref:`bootstrap`.

.. code-block:: bash

  $ python generate_pgp_key.py -h
    usage: generate_pgp_key.py [-h] [--passphrase PASSPHRASE] [--pub PUB]
                               [--priv PRIV] [--armor]
                               name email comment

    Creating public/private PGP keys

    positional arguments:
    name                  PGP user name
    email                 PGP user email
    comment               PGP user comment

    optional arguments:
    -h, --help            show this help message and exit
    --passphrase PASSPHRASE
                          Password to protect the private key. If none, the key
                          is left unlocked
    --pub PUB             Output file for public key [Default: stdout]
    --priv PRIV           Output file for private key [Default: stdout]
    --armor, -a           ASCII armor the output
