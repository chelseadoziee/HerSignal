from chatbot.responses import get_faq_response


def run_chatbot_test():
    print("HerSignal Chatbot Prototype Test")
    print("Type 'quit' to stop.\n")

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() == "quit":
            print("HerSignal: Session ended.")
            break

        response = get_faq_response(user_input)
        print(f"HerSignal: {response}\n")


if __name__ == "__main__":
    run_chatbot_test()