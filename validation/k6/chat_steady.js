import http from "k6/http";
import { check } from "k6";

export const options = {
  insecureSkipTLSVerify: true,
  vus: 20,
  duration: "10m",
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<2500"],
  },
};

const BASE_URL = __ENV.BASE_URL || "https://localhost";

export default function () {
  const payload = JSON.stringify({
    text: "Que servicios usa Zyrabit en su arquitectura local segura?",
  });
  const params = {
    headers: { "Content-Type": "application/json" },
    timeout: "120s",
  };

  const res = http.post(`${BASE_URL}/v1/chat`, payload, params);
  check(res, {
    "status is 200": (r) => r.status === 200,
    "has response field": (r) => r.body.includes("response"),
  });
}
