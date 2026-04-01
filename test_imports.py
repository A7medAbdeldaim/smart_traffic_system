"""
Quick test to verify all modules can be imported
"""

print("Testing module imports...\n")

try:
    print("✓ Testing database module...")
    from database import db_manager, db_config

    print("✓ Testing simulation module...")
    from simulation import demo_sim, sim_config

    print("✓ Testing optimizer module...")
    from optimizer import signal_optimizer, emergency_handler, opt_config

    print("✓ Testing API module...")
    from api import app, app_state

    print("\n✅ All modules imported successfully!")
    print("\nSystem is ready to run. Execute:")
    print("  python main.py")
    print("\n")

except ImportError as e:
    print(f"\n❌ Import error: {e}")
    print("\nPlease install dependencies:")
    print("  pip install -r requirements.txt")
    print("\n")
    exit(1)
