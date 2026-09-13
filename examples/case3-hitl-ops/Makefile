.PHONY: help inbox demo deny reject sample stop clean

help:
	@echo "Case 3 — governed ops agent demo"
	@echo "  make inbox    # start mock ticket inbox :8765"
	@echo "  make demo     # HITL approve → create ticket (inbox must be up)"
	@echo "  make deny     # show policy deny (nmap.scan)"
	@echo "  make reject   # show HITL reject"
	@echo "  make sample   # run inbox+demo then stop (one shot)"
	@echo "  make stop     # stop background inbox if started via make sample"

inbox:
	python3 scripts/mock_ticket_server.py

demo:
	python3 scripts/run_case3.py --profile ops --approve yes --title "Fallo de login en prod" --priority high --requester abraham

deny:
	python3 scripts/run_case3.py --profile ops --deny-tool nmap.scan

reject:
	python3 scripts/run_case3.py --profile ops --approve no --title "Should not create"

sample:
	@mkdir -p out
	@python3 scripts/mock_ticket_server.py > out/server.log 2>&1 & echo $$! > out/server.pid
	@sleep 1
	@python3 scripts/run_case3.py --profile ops --approve yes --title "Fallo de login en prod" --priority high --requester abraham || (kill `cat out/server.pid` 2>/dev/null; exit 1)
	@python3 scripts/run_case3.py --profile ops --deny-tool nmap.scan || true
	@python3 scripts/run_case3.py --profile ops --approve no --title "Should not create" || true
	@kill `cat out/server.pid` 2>/dev/null || true
	@echo "Done. See out/tickets.jsonl and out/audit.jsonl"

stop:
	@kill `cat out/server.pid` 2>/dev/null || true
	@rm -f out/server.pid

clean:
	rm -f out/*.jsonl out/*.log out/*.pid
