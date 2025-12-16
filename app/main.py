import streamlit as st
import io

from app.agents.master_agent import MasterAgent
from app.services.db import init_db
from app.state import LoanSession, Phase # Ensure Phase is imported


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


# --- REVERTED: Now a static utility to display artifacts once at the bottom ---
def display_sanction_letter_artifacts(session: LoanSession) -> None:
    """Renders the final sanction letter preview and download link in a static section."""
    
    # Only run if the process is complete and we have letter data
    if session.phase == Phase.COMPLETED and session.sanction_letter.get("content"):
        
        st.divider() # Visually separate from the chat history
        st.header("📄 Final Loan Artifacts")
        st.success("✅ Application Process Complete!")
        
        letter_content = session.sanction_letter.get("content")
        download_path = session.sanction_letter.get("path")
        
        if letter_content:
            st.subheader("Sanction Letter Preview:")
            
            # Use a unique key based on the loan ID to fix the DuplicateWidgetID error
            unique_key = f"sanction_download_{session.loan_request.get('loan_amount', 'default')}"
            
            with st.expander("Click to view Sanction Letter", expanded=True):
                st.markdown(letter_content)
            
            st.markdown("### Download Full Document")
            
            # Create a mock download button using the content
            mock_pdf_content = io.BytesIO(letter_content.encode('utf-8'))
            
            st.download_button(
                label="Download Sanction Letter (PDF)",
                data=mock_pdf_content,
                file_name=download_path.split('/')[-1],
                mime="application/pdf",
                key=unique_key # <-- CRITICAL FIX: Pass a unique key
            )


def main() -> None:
    init_session()
    session = st.session_state.loan_session
    
    # ... (Phase, Loan Request, KYC Status display remains the same) ...

    # Display current phase and status summary
    st.info(
        f"Phase: **{session.phase.value}** — "
        f"{session.status_summary()}"
    )

    # Display loan request summary
    loan_request = session.loan_request
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

    # Display KYC Status
    customer_profile = session.customer_profile
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
            
    # Render chat conversation
    render_conversation()
    
    # --- NEW PLACEMENT: DISPLAY ARTIFACTS BELOW THE CHAT ---
    display_sanction_letter_artifacts(session)

    # Debug Expander
    with st.expander("Session debug", expanded=False):
        st.json(session.serialize())

    # User Input
    user_input = st.chat_input("Describe your loan needs")
    if user_input:
        response = st.session_state.master_agent.handle_user_message(user_input)
        st.rerun()


if __name__ == "__main__":
    main()