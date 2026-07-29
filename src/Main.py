import traceback
import System

if __name__ == "__main__":
    System.FunctionLibrary.log("Starting system...", System.LogLevel.NONE)
    application = System.Application()

    try:
        System.FunctionLibrary.log("System is running. Press Ctrl+C to stop.", System.LogLevel.NONE)
        application.run()
    except KeyboardInterrupt:
        print("\nStopping system...")
    except Exception:
        System.FunctionLibrary.log( traceback.format_exc(), System.LogLevel.DANGER)
    finally:
        System.FunctionLibrary.log("System has stopped.", System.LogLevel.NONE)
        application.stop()
