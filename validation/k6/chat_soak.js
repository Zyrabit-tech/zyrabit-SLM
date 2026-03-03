import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  insecureSkipTLSVerify: true,
  vus: 10,
  duration: "6h",
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<3000"],
  },
};

const BASE_URL = __ENV.BASE_URL || "https://localhost";

export default function () {
  const payload = JSON.stringify({
    text: "Explica la diferencia entre flujo RAG y respuesta directa en este stack.",
  });
  const params = {
    headers: { "Content-Type": "application/json" },
    timeout: "120s",
  };

  const res = http.post(`${BASE_URL}/v1/chat`, payload, params);
  check(res, {
    "status is 200": (r) => r.status === 200,
  });
  sleep(2);
}

