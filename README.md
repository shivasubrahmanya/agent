# Lead Discovery Chatbot

B2B Lead Discovery and Validation Chatbot powered by Claude API.

## Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API key**:
   - Copy `.env.example` to `.env`
   - Add your Anthropic API key

3. **Run the chatbot**:
   ```bash
   python lead_discovery.py
   ```

## Usage

Enter company details in natural language. Example:
```
Company: Microsoft, Industry: Technology, Size: 150000 employees
Roles: Chief Technology Officer, VP of Engineering
```

The chatbot will return structured JSON with lead verification results.

Type `quit` or `exit` to stop.
