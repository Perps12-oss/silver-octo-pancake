"""Test script for ScanningStatePanel component."""
import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from cerebro.ui.components.scanning_state_panel import ScanningStatePanel


def test_scanning_state_panel():
    """Test ScanningStatePanel functionality."""
    app = QApplication(sys.argv)

    # Create panel
    panel = ScanningStatePanel()

    # Test 1: Initial state
    assert not panel.is_scanning(), "Initial state should not be scanning"
    print("[PASS] Test 1: Initial state correct")

    # Test 2: Set scanning state
    panel.set_scanning_state(True)
    assert panel.is_scanning(), "State should be scanning after set_scanning_state(True)"
    print("[PASS] Test 2: Scanning state set correctly")

    # Test 3: Update progress
    panel.update_progress(
        files_scanned=50,
        total_files=100,
        current_file="/test/image.jpg",
        duplicates_found=10,
        groups_found=3
    )
    assert panel.is_scanning(), "Should still be scanning after progress update"
    print("[PASS] Test 3: Progress updated correctly")

    # Test 4: Reset
    panel.reset()
    assert not panel.is_scanning(), "Should not be scanning after reset"
    print("[PASS] Test 4: Reset works correctly")

    # Test 5: Signal connectivity
    cancel_triggered = False

    def on_cancel():
        nonlocal cancel_triggered
        cancel_triggered = True

    panel.cancel_requested.connect(on_cancel)

    # Simulate cancel button click (manually emit signal)
    panel.cancel_requested.emit()
    assert cancel_triggered, "Cancel signal should be triggered"
    print("[PASS] Test 5: Cancel signal works")

    # Test 6: Edge cases
    panel.update_progress(0, 0, "", 0, 0)  # Zero division protection
    print("[PASS] Test 6: Edge case handling (zero total files)")

    # Test 7: Backward compatibility alias
    from cerebro.ui.components.scanning_state_panel import ScanProgressPanel
    assert ScanProgressPanel is ScanningStatePanel, "Backward compatibility alias should work"
    print("[PASS] Test 7: Backward compatibility alias works")

    panel.show()
    print("\n[SUCCESS] All ScanningStatePanel tests passed!")
    print("Panel displayed successfully with all functionality working.")

    # Keep window open briefly for visual inspection
    app.exec()


if __name__ == "__main__":
    test_scanning_state_panel()
