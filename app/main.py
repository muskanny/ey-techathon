import streamlit as st

from app.agents.master_agent import MasterAgent
from app.state import LoanSession


st.set_page_config(page_title="AI Loan Agent", page_icon=":bank:")
st.title("AI-powered Personal Loan Assistant")
st.caption("Techathon demo – multi-agent workflow (LangChain/LangGraph)")


def init_session() -> None:
    if "loan_session" not in st.session_state:
        st.session_state.loan_session = LoanSession()
    if "master_agent" not in st.session_state:
        st.session_state.master_agent = MasterAgent(session=st.session_state.loan_session)


def render_conversation() -> None:
    for msg in st.session_state.loan_session.messages:
        with st.chat_message(msg.role):
            st.markdown(msg.content)


def main() -> None:
    init_session()
    st.info(
        f"Phase: **{st.session_state.loan_session.phase.value}** — "
        f"{st.session_state.loan_session.status_summary()}"
    )
    render_conversation()
    with st.expander("Session debug", expanded=False):
        st.json(st.session_state.loan_session.serialize())

    user_input = st.chat_input("Describe your loan needs")
    if user_input:
        response = st.session_state.master_agent.handle_user_message(user_input)
        st.experimental_rerun()


if __name__ == "__main__":
    main()
