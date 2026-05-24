APP_DIR    := $(shell pwd)
DIST_BIN   := $(APP_DIR)/dist/grfeditorpy/grfeditorpy
DESKTOP_DIR := $(HOME)/.local/share/applications

.PHONY: build clean install-desktop uninstall-desktop verify

build:
	@bash $(APP_DIR)/build.sh

clean:
	rm -rf $(APP_DIR)/build $(APP_DIR)/dist

install-desktop: $(DIST_BIN)
	@install -Dm644 $(APP_DIR)/grfeditorpy.desktop $(DESKTOP_DIR)/grfeditorpy.desktop
	@sed -i "s|Exec=.*|Exec=$(DIST_BIN) %f|" $(DESKTOP_DIR)/grfeditorpy.desktop
	@update-desktop-database $(DESKTOP_DIR) 2>/dev/null || true
	@echo "Desktop entry installed — GRF Editor should now appear in your app launcher."

uninstall-desktop:
	rm -f $(DESKTOP_DIR)/grfeditorpy.desktop
	@update-desktop-database $(DESKTOP_DIR) 2>/dev/null || true

verify:
	@echo "=== Binary check ==="
	@test -x $(DIST_BIN) || (echo "Binary not found. Run 'make build' first." && exit 1)
	@echo "Binary:  $(DIST_BIN)"
	@echo "Size:    $$(du -sh $$(dirname $(DIST_BIN)) | cut -f1)"
	@echo "XCB:     $$(find $$(dirname $(DIST_BIN)) -name 'libqxcb.so' | head -1)"
	@echo ""
	@echo "To debug plugin loading:"
	@echo "  QT_DEBUG_PLUGINS=1 $(DIST_BIN) 2>&1 | head -60"

$(DIST_BIN):
	@echo "Binary not found. Run 'make build' first." && exit 1
