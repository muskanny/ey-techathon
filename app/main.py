import streamlit as st

from app.agents.master_agent import MasterAgent
from app.services.db import init_db
from app.state import LoanSession


st.set_page_config(page_title="AI Loan Agent", page_icon=":bank:")
st.title("AI-powered Personal Loan Assistant")
st.caption("Techathon demo – multi-agent workflow (LangChain/LangGraph)")


def init_session() -> None:
    init_db()
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

    loan_request = st.session_state.loan_session.loan_request
    if loan_request:
        product = loan_request.get("recommended_product")
        st.markdown(
            """
            **Loan request summary**

            - Amount: INR {amount:,.0f}
            - Purpose: {purpose}
            {product_line}
            """.format(
                amount=loan_request.get("loan_amount", 0),
                purpose=loan_request.get("purpose", "-"),
                product_line=(
                    f"- Recommended product: {product['name']} at {product['interest_rate']}%"
                    if product
                    else "- Recommended product: Pending"
                ),
            )
        )

    customer_profile = st.session_state.loan_session.customer_profile
    if customer_profile:
        if customer_profile.get("verified"):
            customer = customer_profile.get("customer", {})
            st.success(
                f"KYC verified for {customer.get('name', 'customer')} (PAN {customer_profile.get('pan')})."
            )
        else:
            st.warning(
                "KYC pending: " + customer_profile.get("reason", "Awaiting correct details.")
            )
    render_conversation()
    with st.expander("Session debug", expanded=False):
        st.json(st.session_state.loan_session.serialize())

    user_input = st.chat_input("Describe your loan needs")
    if user_input:
        response = st.session_state.master_agent.handle_user_message(user_input)
        st.rerun()


if __name__ == "__main__":
    main()
