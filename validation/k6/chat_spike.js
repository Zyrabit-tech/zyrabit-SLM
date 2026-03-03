import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  insecureSkipTLSVerify: true,
  stages: [
    { duration: "30s", target: 100 },
    { duration: "2m", target: 100 },
    { duration: "60s", target: 0 },
  ],
  thresholds: {
    http_req_failed: ["rate<0.02"],
    http_req_duration: ["p(95)<4000"],
  },
};

const BASE_URL = __ENV.BASE_URL || "https://localhost";

export default function () {
  const payload = JSON.stringify({
    text: "Resume la topologia de servicios de Zyrabit y su capa de seguridad.",
  });
  const params = {
    headers: { "Content-Type": "application/json" },
    timeout: "120s",
  };

  const res = http.post(`${BASE_URL}/v1/chat`, payload, params);
  check(res, {
    "status is 200 or 400": (r) => r.status === 200 || r.status === 400,
  });
  sleep(1);
}

