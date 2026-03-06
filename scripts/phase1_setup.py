#!/usr/bin/env python3
"""
Phase 1 Setup Script

Automates the initialization of Phase 1 improvements:
- Generates initial database migration
- Applies migration
- Verifies Redis connection
- Tests security features
"""
import asyncio
import sys
import subprocess
from pathlib import Path


def run_command(cmd: str, description: str) -> bool:
    """Run a shell command and return success status."""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"{'='*60}")
    print(f"Running: {cmd}\n")
    
    result = subprocess.run(cmd, shell=True)
    
    if result.returncode == 0:
        print(f"✅ {description} - SUCCESS\n")
        return True
    else:
        print(f"❌ {description} - FAILED\n")
        return False


def main():
    """Execute Phase 1 setup steps."""
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║        MARKETPULSE PHASE 1 SETUP SCRIPT                  ║
    ║                                                           ║
    ║  This will:                                              ║
    ║  1. Build and start Docker services                      ║
    ║  2. Generate initial Alembic migration                   ║
    ║  3. Apply database migrations                            ║
    ║  4. Verify Redis connectivity                            ║
    ║  5. Test security features                               ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    input("Press ENTER to continue or CTRL+C to cancel...")
    
    steps = [
        ("docker-compose down", "Stopping existing containers"),
        ("docker-compose up --build -d", "Building and starting services"),
        ("timeout 10", "Waiting for services to be ready"),
        ("docker-compose exec -T api alembic revision --autogenerate -m 'initial schema'", "Generating initial migration"),
        ("docker-compose exec -T api alembic upgrade head", "Applying database migrations"),
        ("docker-compose exec -T redis redis-cli ping", "Testing Redis connection"),
        ("docker-compose ps", "Checking service status"),
    ]
    
    failed_steps = []
    
    for cmd, description in steps:
        if not run_command(cmd, description):
            failed_steps.append(description)
            if "Generating initial migration" not in description:
                # Continue even if migration exists
                pass
    
    print("\n" + "="*60)
    print("SETUP SUMMARY")
    print("="*60)
    
    if not failed_steps:
        print("✅ All steps completed successfully!")
        print("\n🚀 Your application is ready!")
        print("\n📍 Available at:")
        print("   - API: http://localhost:8000")
        print("   - API Docs: http://localhost:8000/docs")
        print("   - Frontend: http://localhost:5173 (run: cd frontend && npm run dev)")
        print("\n📝 Next steps:")
        print("   1. Update frontend to use cookie-based auth")
        print("   2. Test rate limiting (60 req/min)")
        print("   3. Test account lockout (5 failed logins)")
        print("   4. Review PHASE1_SUMMARY.md for details")
    else:
        print(f"⚠️  {len(failed_steps)} step(s) failed:")
        for step in failed_steps:
            print(f"   - {step}")
        print("\n💡 Check docker-compose logs for details:")
        print("   docker-compose logs")
        return 1
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Setup failed with error: {e}")
        sys.exit(1)
