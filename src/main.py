import System

if __name__ == "__main__":
    System.FunctionLibrary.log("Starting system...", System.LogLevel.DANGER)
    application = System.Application()

    try:
        System.FunctionLibrary.log("System is running. Press Ctrl+C to stop.", System.LogLevel.NONE)
        application.run()
    except Exception as e:
        System.FunctionLibrary.log(f"An error occurred: {e}", System.LogLevel.DANGER)
    except KeyboardInterrupt:
        print("\nStopping system...")
    finally:
        System.FunctionLibrary.log("System has stopped.", System.LogLevel.NONE)
        application.stop()
