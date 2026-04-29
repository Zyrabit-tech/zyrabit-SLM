# Zyrabit-TT-Bridge

Bridge de simulacion para validar Qwen 2.5 7B-Instruct contra el stack TT-MLIR/tt-forge de Tenstorrent, con fallback deterministico para entornos Docker de Mac M-series sin hardware o sin RAM suficiente.

## Docker local

```bash
docker build -t zyrabit-tt-bridge:mock internal/engine/tenstorrent
docker run --rm -p 8090:8090 zyrabit-tt-bridge:mock
```

```bash
curl -fsS http://localhost:8090/v1/health
curl -fsS -X POST http://localhost:8090/v1/generate \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Valida Qwen 2.5 7B en TT-MLIR","max_new_tokens":64}'
```

## Docker Compose

```bash
docker compose -f zyrabit-slm/docker-compose.yml --profile tenstorrent up --build zyrabit-tt-bridge
```

## Tenstorrent real

El build mock es el default para que la demo corra en Mac M-series. Para intentar instalar wheels Tenstorrent desde el indice privado:

```bash
docker build \
  --build-arg INSTALL_TENSTORRENT=true \
  --build-arg TENSTORRENT_PYPI_URL=https://pypi.eng.aws.tenstorrent.com/ \
  -t zyrabit-tt-bridge:tt \
  internal/engine/tenstorrent
```

Variables principales:

- `ZYRABIT_TT_MODE=mock|auto|tt-sim`
- `ZYRABIT_TT_MODEL_ID=Qwen/Qwen2.5-7B-Instruct`
- `ZYRABIT_TT_MIN_RAM_GB=24`
- `ZYRABIT_TT_ALLOW_REMOTE_MODEL=false`
