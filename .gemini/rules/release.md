---
description: KeyStone sürüm ve release kuralları
globs: *
---
# Sürüm ve Release Kuralı

KeyStone uygulamasında release yapılırken:
- Her release işleminde sürüm patch seviyesinde **+0.0.1** artırılır (örn. 3.1.0 -> 3.1.1 -> 3.1.2).
- Sürüm hem `pyproject.toml` (`version = "..."`) hem de `keystone/__init__.py` (`__version__ = "..."`) dosyalarında güncellenir.
- Commit oluşturulduktan sonra `v<sürüm>` (örn. `v3.1.1`) etiketi (tag) basılır.
- Commit ve tag GitHub'a (`git push origin main` ve `git push origin v<sürüm>`) push edilir. Bu işlem GitHub Actions üzerindeki Build & Release iş akışını tetikler ve binary release'leri otomatik üretir.
