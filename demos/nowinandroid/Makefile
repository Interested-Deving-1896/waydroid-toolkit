# Makefile for running Gradle tasks against the nowinandroid subtree.
# Ported from canonical/anbox-cloud-demos (Apache-2.0).
# amc/Anbox commands replaced with wdt/Waydroid equivalents.

APP_DIR := app

.PHONY: help
help:
	@echo "Available targets for 'nowinandroid':"
	@echo "  nia-build            Build DemoDebug APK"
	@echo "  nia-install          Install DemoDebug APK on connected device"
	@echo "  nia-lint             Run lint checks"
	@echo "  nia-unit-test        Run unit tests"
	@echo "  nia-screenshot-test  Run Roborazzi screenshot tests"
	@echo "  nia-e2e-test         Run E2E instrumented tests (requires Waydroid ADB)"
	@echo "  nia-clean            Clean build directory"
	@echo "  nia-tasks            List available Gradle tasks"
	@echo ""
	@echo "Waydroid helpers:"
	@echo "  waydroid-start       Start Waydroid session"
	@echo "  waydroid-adb         Connect ADB to Waydroid"
	@echo "  waydroid-stop        Stop Waydroid session"

.PHONY: nia-build
nia-build:
	./$(APP_DIR)/gradlew -p $(APP_DIR) :app:assembleDemoDebug

.PHONY: nia-install
nia-install:
	./$(APP_DIR)/gradlew -p $(APP_DIR) :app:installDemoDebug

.PHONY: nia-lint
nia-lint:
	./$(APP_DIR)/gradlew -p $(APP_DIR) :app:lintDemoDebug

.PHONY: nia-unit-test
nia-unit-test:
	./$(APP_DIR)/gradlew -p $(APP_DIR) :app:testDemoDebugUnitTest

.PHONY: nia-screenshot-test
nia-screenshot-test:
	./$(APP_DIR)/gradlew -p $(APP_DIR) :app:compareRoborazziDemoDebug

.PHONY: nia-e2e-test
nia-e2e-test:
	./$(APP_DIR)/gradlew -p $(APP_DIR) :app:connectedDemoDebugAndroidTest

.PHONY: nia-clean
nia-clean:
	./$(APP_DIR)/gradlew -p $(APP_DIR) app:clean

.PHONY: nia-tasks
nia-tasks:
	./$(APP_DIR)/gradlew -p $(APP_DIR) :app:tasks

# ── Waydroid helpers ──────────────────────────────────────────────────────────

.PHONY: waydroid-start
waydroid-start:
	waydroid session start &
	@echo "Waiting for Waydroid session..."
	@for i in $$(seq 1 30); do \
		waydroid status 2>/dev/null | grep -q "Session:.*RUNNING" && break; \
		sleep 2; \
	done
	@waydroid status

.PHONY: waydroid-adb
waydroid-adb:
	@# Connect ADB to the Waydroid container
	@ADB_ADDR=$$(waydroid prop get waydroid.host.address 2>/dev/null || echo "192.168.240.112"); \
	adb connect "$$ADB_ADDR":5555 || adb connect localhost:5555
	adb wait-for-device
	@echo "ADB connected"

.PHONY: waydroid-stop
waydroid-stop:
	waydroid session stop
