
import asyncio
import speech_recognition as sr

from agent import create_expense_agent, process_message


def listen_for_speech():
    recognizer = sr.Recognizer()

    with sr.Microphone() as source:
        print("\nListening... Speak your expense.")
        recognizer.adjust_for_ambient_noise(
            source, duration=0.5
        )

        try:
            audio = recognizer.listen(
                source,
                timeout=10,
                phrase_time_limit=15,
            )
        except sr.WaitTimeoutError:
            print("No speech detected. Please try again.")
            return None

    try:
        text = recognizer.recognize_google(audio)
        print(f"\nYou said: {text}")
        return text

    except sr.UnknownValueError:
        print("Sorry, I couldn't understand that.")
        return None

    except sr.RequestError as error:
        print(f"Speech recognition service error: {error}")
        return None


async def main():
    # Create the agent once, not for every recording.
    agent = await create_expense_agent()
    messages = []

    print("\nVoice Expense Agent ready!")
    print("Speak a transaction or ask a question.")
    print("Say 'exit' to quit.\n")

    while True:
        user_message = listen_for_speech()

        if not user_message:
            continue

        if user_message.strip().lower() in {
            "exit", "quit", "stop"
        }:
            print("Goodbye!")
            break

        try:
            messages = await process_message(
                agent, messages, user_message
            )
        except Exception as exc:
            print(f"\nRequest failed: {exc}\n")


if __name__ == "__main__":
    asyncio.run(main())
