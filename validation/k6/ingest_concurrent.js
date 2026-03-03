import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  insecureSkipTLSVerify: true,
  vus: 10,
  duration: "5m",
  thresholds: {
    http_req_failed: ["rate<0.02"],
    http_req_duration: ["p(95)<5000"],
  },
};

const BASE_URL = __ENV.BASE_URL || "https://localhost";
const DOC_PATH =
  __ENV.DOC_PATH ||
  "../../zyrabit-brain-api/api-rag/sample_docs/zyrabit_project_overview.txt";

const fileBinary = open(DOC_PATH, "b");

export default function () {
  const data = {
    file: http.file(fileBinary, "zyrabit_project_overview.txt", "text/plain"),
  };
  const res = http.post(`${BASE_URL}/v1/ingest`, data, { timeout: "120s" });

  check(res, {
    "status is 200 or 413": (r) => r.status === 200 || r.status === 413,
  });
  sleep(1);
}

