Preferences vector storage,I would give it a transaction once, and next time I could just say salary credited and it would understand the payment method and amount and all by itself
and other such similar preferences

Also, like
    suppose I added a transaction for coffee via voice in a live day
    and after an hour, I say, nevermind remove the coffee transaction, then it has to remove the last added one, as I drink coffee everyday
    how would we solve this

Also, what if one prompt by user needs 2-3 mcp tool calls together

Also, as the agent will be local in future, we need to have a tool that updates it regarding current day date week month etc details
    so it can perform things like, summarize transactions from day before yesterday, or last wednesday

Cool, now lets start with the app
    For the app my idea is
        basically I want to make it as a widget that will stay on my homescreen page 2
        such that it has two options there, mic and type
            mic one starts the voice agent which listens request, prints it out below in the widget space itself after hearing, and once I press ok/send button, it goes ahead
            and for type, once I type and press the ok/send button, it goes ahead
            and prints the latest success/followup response there it self
        the entire convos/chat will be available when I specifically open the app, not in the widget
        widget is only for recording

        the main app on opening would look like a basic chatbot with all these convos
        and one tab where I can view the raw db in table form

        is this possible

uv run uvicorn api:app --host 0.0.0.0 --port 8000