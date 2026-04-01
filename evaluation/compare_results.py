"""
Compare baseline vs AI-optimized results
"""
import json
import os


def compare_results():
    """Compare and display results from baseline and AI runs"""

    baseline_file = 'evaluation/baseline_results.json'
    ai_file = 'evaluation/ai_results.json'

    # Check if files exist
    if not os.path.exists(baseline_file):
        print(f"❌ Baseline results not found: {baseline_file}")
        print("   Run: python evaluation/run_baseline.py")
        return

    if not os.path.exists(ai_file):
        print(f"❌ AI results not found: {ai_file}")
        print("   Run: python evaluation/run_ai.py")
        return

    # Load results
    with open(baseline_file, 'r') as f:
        baseline = json.load(f)

    with open(ai_file, 'r') as f:
        ai = json.load(f)

    # Calculate improvements
    wait_improvement = ((baseline['avg_wait_time'] - ai['avg_wait_time']) / baseline['avg_wait_time']) * 100
    throughput_improvement = ((ai['throughput'] - baseline['throughput']) / baseline['throughput']) * 100

    # Display comparison
    print("\n" + "=" * 80)
    print("PERFORMANCE COMPARISON - Baseline vs AI-Optimized")
    print("=" * 80 + "\n")

    print(f"{'Metric':<30} {'Baseline':<20} {'AI-Optimized':<20} {'Improvement':<15}")
    print("-" * 80)

    print(f"{'Average Wait Time':<30} {baseline['avg_wait_time']:<20.2f} "
          f"{ai['avg_wait_time']:<20.2f} {wait_improvement:>+14.1f}%")

    print(f"{'Total Vehicles':<30} {baseline['total_vehicles']:<20} "
          f"{ai['total_vehicles']:<20} {((ai['total_vehicles'] - baseline['total_vehicles']) / baseline['total_vehicles'] * 100):>+14.1f}%")

    print(f"{'Throughput (veh/min)':<30} {baseline['throughput']:<20.2f} "
          f"{ai['throughput']:<20.2f} {throughput_improvement:>+14.1f}%")

    print("\n" + "=" * 80)

    # Summary
    print("\n📊 SUMMARY\n")
    print(f"  • The AI-optimized system reduced average wait time by {wait_improvement:.1f}%")
    print(f"  • Throughput improved by {throughput_improvement:.1f}%")

    if wait_improvement > 30:
        print(f"  • ✅ Excellent performance - {wait_improvement:.0f}% improvement exceeds target!")
    elif wait_improvement > 20:
        print(f"  • ✅ Good performance - {wait_improvement:.0f}% improvement achieved")
    else:
        print(f"  • ⚠️  Moderate performance - {wait_improvement:.0f}% improvement")

    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    compare_results()
