#!/usr/bin/env python3
"""
Temperature Agent CLI - Interactive command-line interface.

Usage:
    python -m temperature_agent              # Start interactive chat
    python -m temperature_agent --clear-memory  # Clear memory and exit

This provides a simple chat interface to interact with the temperature agent.
Requires AgentCore Memory to be configured in config.json.
"""

import argparse
import sys
import readline  # Enables command history with up/down arrows

from temperature_agent.config import get_config


def get_model_config() -> tuple[str, str]:
    """Get model and region from config."""
    try:
        config = get_config()
        model_id = config.get("bedrock_model", "qwen.qwen3-32b-v1:0")
        region = config.get("bedrock_region", "us-east-1")
        return model_id, region
    except Exception:
        return "qwen.qwen3-32b-v1:0", "us-east-1"


def print_greeting():
    """Print the startup greeting with current status."""
    print("\n" + "=" * 60)
    try:
        from temperature_agent.agent_with_memory import generate_status_greeting
        greeting = generate_status_greeting()
        print(greeting)
    except Exception as e:
        print("🌡️ Temperature Assistant")
        print(f"\n⚠️  Could not fetch current status: {e}")
        print("\nHow can I help you?")
    print("=" * 60 + "\n")


def print_help():
    """Print help information."""
    print("""
Commands:
  /help     - Show this help message
  /status   - Show current temperature status
  /quit     - Exit the chat
  /exit     - Exit the chat

Just type your question or command and press Enter!

Example queries:
  - Which room is coldest?
  - What's the forecast?
  - Send me an alert about the basement
  - Set the attic threshold to 50 degrees
  - The kitchen pipes run along the north wall
  - Why is the attic so cold?
  - Show my alert history
""")


def run_cli(model_id: str, region: str):
    """Run the CLI."""
    from temperature_agent.agent_with_memory import create_agent
    
    try:
        agent = create_agent(model_id=model_id, region=region)
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("\nPlease configure AgentCore Memory in config.json.")
        print("See docs/agentcore_memory_setup.md for instructions.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error creating agent: {e}")
        sys.exit(1)
    
    print("✅ Agent ready!")
    print_greeting()
    print("Type /help for commands, or just ask a question.")
    print("Type /quit to exit.\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye! 👋")
            break
        
        if not user_input:
            continue
        
        if user_input.lower() in ["/quit", "/exit", "quit", "exit"]:
            print("\nGoodbye! 👋")
            break
        
        if user_input.lower() in ["/help", "help", "?"]:
            print_help()
            continue
        
        if user_input.lower() in ["/status", "status"]:
            print_greeting()
            continue
        
        print("\nAssistant: ", end="", flush=True)
        
        try:
            response = agent(user_input)
            # Response was already streamed to stdout
        except Exception as e:
            print(f"\n❌ Error: {e}")
        
        print()


def clear_agentcore_memory(memory_id: str, region: str, verbose: bool = False) -> dict:
    """
    Clear all records from AgentCore Memory without deleting the resource.
    
    Returns:
        dict with success status and count of deleted records
    """
    import boto3
    
    client = boto3.client('bedrock-agentcore', region_name=region)
    
    # Known namespaces used by our agent
    namespaces = [
        "/actor/default_user/house",
        "/actor/cli_user/house",
    ]
    
    total_deleted = 0
    errors = []
    
    for namespace in namespaces:
        try:
            # List all records in this namespace
            paginator = client.get_paginator('list_memory_records')
            record_ids = []
            
            for page in paginator.paginate(memoryId=memory_id, namespace=namespace):
                for record in page.get('memoryRecordSummaries', []):
                    record_ids.append(record['memoryRecordId'])
            
            if verbose:
                print(f"    Namespace {namespace}: found {len(record_ids)} records")
            
            if not record_ids:
                continue
            
            # Batch delete (max 100 at a time)
            for i in range(0, len(record_ids), 100):
                batch = record_ids[i:i+100]
                records_to_delete = [{'memoryRecordId': rid} for rid in batch]
                
                if verbose:
                    print(f"    Deleting: {batch}")
                
                response = client.batch_delete_memory_records(
                    memoryId=memory_id,
                    records=records_to_delete
                )
                
                if verbose:
                    print(f"    Response: successful={len(response.get('successfulRecords', []))}, failed={len(response.get('failedRecords', []))}")
                
                # Check for failures
                failed = response.get('failedRecords', [])
                if failed:
                    errors.extend([f"Failed to delete {f['memoryRecordId']}: {f.get('errorMessage', 'unknown')}" for f in failed])
                
                total_deleted += len(batch) - len(failed)
                
        except client.exceptions.ResourceNotFoundException:
            # Namespace doesn't exist, that's fine
            if verbose:
                print(f"    Namespace {namespace}: not found (ok)")
            continue
        except Exception as e:
            errors.append(f"Error clearing namespace {namespace}: {e}")
    
    return {
        "success": len(errors) == 0,
        "deleted_count": total_deleted,
        "errors": errors
    }


def clear_memory():
    """Clear AgentCore Memory and local alert history."""
    from temperature_agent.tools.memory import clear_alert_history
    
    print("\n🗑️  Clearing memory...")
    
    # Clear local alert history
    print("\nAlert history:")
    result = clear_alert_history()
    if result.get("success"):
        print(f"  ✅ Cleared: {', '.join(result.get('cleared', []))}")
    else:
        print(f"  ❌ Error: {result.get('error')}")
    
    # Clear AgentCore Memory
    config = get_config()
    memory_id = config.get("agentcore_memory_id")
    region = config.get("bedrock_region", "us-east-1")
    
    if memory_id:
        print("\nAgentCore Memory:")
        try:
            ac_result = clear_agentcore_memory(memory_id, region)
            if ac_result.get("success"):
                count = ac_result.get('deleted_count', 0)
                print(f"  ✅ Deleted {count} memory records")
                if count > 0:
                    print("     (Note: May take 30-60 seconds to fully propagate)")
            else:
                print(f"  ⚠️  Deleted {ac_result.get('deleted_count', 0)} records with errors:")
                for error in ac_result.get("errors", []):
                    print(f"     ❌ {error}")
        except Exception as e:
            print(f"  ❌ Failed to clear AgentCore Memory: {e}")
    else:
        print("\nAgentCore Memory:")
        print("  ⚠️  Not configured (agentcore_memory_id missing in config.json)")
    
    print()


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Temperature Agent CLI - Interactive temperature monitoring assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m temperature_agent              Start interactive chat
  python -m temperature_agent --clear-memory  Clear memory and exit
        """
    )
    parser.add_argument(
        "--clear-memory",
        action="store_true",
        help="Clear AgentCore Memory and alert history, then exit"
    )
    return parser.parse_args()


def main():
    """Run the interactive CLI."""
    args = parse_args()
    
    # Handle --clear-memory
    if args.clear_memory:
        clear_memory()
        return
    
    model_id, region = get_model_config()
    
    print("\n🌡️  Starting Temperature Agent...")
    print(f"(Model: {model_id})")
    print()
    
    run_cli(model_id, region)


if __name__ == "__main__":
    main()
