# SIP Insight Lab — PII Spot-Check QA Report (Task 2.7)

- **Date & Time:** 2026-10-31T16:12:43.856676+00:00
- **Sample Size:** 50 items
- **PII Leaks Detected:** 0
- **Status:** **PASS** (Target: 0 leaks)

---

## Checked Sample Items

| # | Item ID | Source | Lang | Snippet | Redacted Log | Leak? |
|---|---|---|---|---|---|---|
| 1 | `de5ca018` | reddit | en | Had insufficient balance on debit date because salary was delayed. Did not know ... | `{"total_redacted": 0}` | No |
| 2 | `cd3c2388` | play_store | en | My SIP was auto cancelled after 3 failed debits due to bank server issue at SBI.... | `{"PHONE": 1, "total_redacted": 1}` | No |
| 3 | `d98e4e8d` | reddit | en | My uncle told me stock market is gambling and asked me to cancel mutual fund and... | `{"total_redacted": 0}` | No |
| 4 | `ca9dca1f` | reddit | en | Been doing SIP in Parag Parikh Flexi Cap for 2 years now. Rupee cost averaging r... | `{"total_redacted": 0}` | No |
| 5 | `9afec6dd` | reddit | en | Had insufficient balance on debit date because salary was delayed. Did not know ... | `{"total_redacted": 0}` | No |
| 6 | `e5a6de80` | play_store | en | Clean UI, smooth auto-debit on salary day. Set it and forget it. Very happy with... | `{"total_redacted": 0}` | No |
| 7 | `4cd2f9a2` | play_store | en | My SIP was auto cancelled after 3 failed debits due to bank server issue at SBI.... | `{"PHONE": 1, "total_redacted": 1}` | No |
| 8 | `47b2220b` | youtube | en | Started with 500 rs SIP 1 year ago, seeing good compounding now. Highly recommen... | `{"total_redacted": 0}` | No |
| 9 | `4c73b01d` | tradingqa | en | Switching from active large cap fund to Nifty 50 index fund on Groww. Stopped th... | `{"total_redacted": 0}` | No |
| 10 | `475c933f` | play_store | en | My SIP was auto cancelled after 3 failed debits due to bank server issue at SBI.... | `{"PHONE": 1, "total_redacted": 1}` | No |
| 11 | `115da69f` | youtube | en | Started with 500 rs SIP 1 year ago, seeing good compounding now. Highly recommen... | `{"total_redacted": 0}` | No |
| 12 | `8a21b435` | youtube | en | I do not understand what NAV means. If NAV is high does it mean I am getting les... | `{"total_redacted": 0}` | No |
| 13 | `3254d598` | youtube | en | I do not understand what NAV means. If NAV is high does it mean I am getting les... | `{"total_redacted": 0}` | No |
| 14 | `ea137769` | reddit | en | Hit my financial goal for house downpayment after 3 years of disciplined SIP. St... | `{"total_redacted": 0}` | No |
| 15 | `590cc115` | youtube | hi | म्यूचुअल फंड में हर महीने 1000 रुपये का एसआईपी करना बहुत आसान है। बहुत बढ़िया जा... | `{"total_redacted": 0}` | No |
| 16 | `df824348` | reddit | en | Had insufficient balance on debit date because salary was delayed. Did not know ... | `{"total_redacted": 0}` | No |
| 17 | `a0ab6910` | reddit | en | Trying to change my SIP debit date from 5th to 10th. The modify flow is complete... | `{"total_redacted": 0}` | No |
| 18 | `9d63280d` | tradingqa | en | NACH mandate rejection error on Groww. UPI ID is [REDACTED:UPI_ID]. How to resta... | `{"UPI_ID": 1, "total_redacted": 1}` | No |
| 19 | `dec1f256` | app_store | en | KYC documentation rejected 4 times without clear reason. PAN [REDACTED:PAN] is v... | `{"PAN": 1, "total_redacted": 1}` | No |
| 20 | `81389a97` | reddit | en | Hit my financial goal for house downpayment after 3 years of disciplined SIP. St... | `{"total_redacted": 0}` | No |
| 21 | `c9355193` | reddit | en | Had insufficient balance on debit date because salary was delayed. Did not know ... | `{"total_redacted": 0}` | No |
| 22 | `8b0cfbf9` | play_store | hi | मेरा SIP अपने आप रद्द हो गया क्योंकि बैंक से पैसा नहीं कटा। ग्रो ऐप में कोई सूचन... | `{"total_redacted": 0}` | No |
| 23 | `9477bb59` | play_store | hi | मेरा SIP अपने आप रद्द हो गया क्योंकि बैंक से पैसा नहीं कटा। ग्रो ऐप में कोई सूचन... | `{"total_redacted": 0}` | No |
| 24 | `f2bcc38d` | youtube | en | I do not understand what NAV means. If NAV is high does it mean I am getting les... | `{"total_redacted": 0}` | No |
| 25 | `ce3c4430` | reddit | en | My uncle told me stock market is gambling and asked me to cancel mutual fund and... | `{"total_redacted": 0}` | No |
| 26 | `cc48e274` | tradingqa | en | Switching from active large cap fund to Nifty 50 index fund on Groww. Stopped th... | `{"total_redacted": 0}` | No |
| 27 | `73de950a` | reddit | en | Hit my financial goal for house downpayment after 3 years of disciplined SIP. St... | `{"total_redacted": 0}` | No |
| 28 | `53546bf5` | play_store | en | Why was money deducted when market was closed on Sunday? Groww stole my 2000 rup... | `{"total_redacted": 0}` | No |
| 29 | `d478fe86` | play_store | en | Finfluencer on YouTube promised 20% returns in mutual funds. I am losing money e... | `{"total_redacted": 0}` | No |
| 30 | `5db3ede2` | play_store | en | Clean UI, smooth auto-debit on salary day. Set it and forget it. Very happy with... | `{"total_redacted": 0}` | No |
| 31 | `51ec51b8` | tradingqa | en | Switching from active large cap fund to Nifty 50 index fund on Groww. Stopped th... | `{"total_redacted": 0}` | No |
| 32 | `cc50a9f5` | play_store | en | Very confusing interface after recent update. Cannot find the button to pause my... | `{"total_redacted": 0}` | No |
| 33 | `72c63c6d` | youtube | en | Started with 500 rs SIP 1 year ago, seeing good compounding now. Highly recommen... | `{"total_redacted": 0}` | No |
| 34 | `feba5b68` | app_store | en | Mandate failed for my HDFC account and Groww gave no alert! Email me at [REDACTE... | `{"EMAIL": 1, "AADHAAR": 1, "total_redacted": 2}` | No |
| 35 | `2eca3e8f` | reddit | en | Invested for 6 months in small cap fund. Calculator showed 18% CAGR but portfoli... | `{"total_redacted": 0}` | No |
| 36 | `51535540` | reddit | en | Trying to change my SIP debit date from 5th to 10th. The modify flow is complete... | `{"total_redacted": 0}` | No |
| 37 | `01972fa3` | youtube | en | Started with 500 rs SIP 1 year ago, seeing good compounding now. Highly recommen... | `{"total_redacted": 0}` | No |
| 38 | `4ef7a9f1` | app_store | en | Mandate failed for my HDFC account and Groww gave no alert! Email me at [REDACTE... | `{"EMAIL": 1, "AADHAAR": 1, "total_redacted": 2}` | No |
| 39 | `1095df9c` | reddit | en | Trying to change my SIP debit date from 5th to 10th. The modify flow is complete... | `{"total_redacted": 0}` | No |
| 40 | `9913832f` | play_store | en | Very confusing interface after recent update. Cannot find the button to pause my... | `{"total_redacted": 0}` | No |
| 41 | `84942a81` | tradingqa | en | Market correction scared me. Nifty fell 800 points and my mutual fund SIP value ... | `{"total_redacted": 0}` | No |
| 42 | `115fac1d` | app_store | en | KYC documentation rejected 4 times without clear reason. PAN [REDACTED:PAN] is v... | `{"PAN": 1, "total_redacted": 1}` | No |
| 43 | `b95cf6c3` | youtube | en | I do not understand what NAV means. If NAV is high does it mean I am getting les... | `{"total_redacted": 0}` | No |
| 44 | `c4cce089` | app_store | en | Mandate failed for my HDFC account and Groww gave no alert! Email me at [REDACTE... | `{"EMAIL": 1, "AADHAAR": 1, "total_redacted": 2}` | No |
| 45 | `29e128a7` | reddit | en | Trying to change my SIP debit date from 5th to 10th. The modify flow is complete... | `{"total_redacted": 0}` | No |
| 46 | `fed36058` | app_store | en | Mandate failed for my HDFC account and Groww gave no alert! Email me at [REDACTE... | `{"EMAIL": 1, "AADHAAR": 1, "total_redacted": 2}` | No |
| 47 | `3575a49f` | youtube | en | Sir my SIP was debited from bank but not showing in Groww app. Customer care not... | `{"total_redacted": 0}` | No |
| 48 | `efbdcb5e` | tradingqa | en | Market correction scared me. Nifty fell 800 points and my mutual fund SIP value ... | `{"total_redacted": 0}` | No |
| 49 | `8df0713d` | reddit | en | Been doing SIP in Parag Parikh Flexi Cap for 2 years now. Rupee cost averaging r... | `{"total_redacted": 0}` | No |
| 50 | `31691c0d` | reddit | en | My uncle told me stock market is gambling and asked me to cancel mutual fund and... | `{"total_redacted": 0}` | No |

## Sign-off
- **Reviewed by:** Growth PM & AI Researcher
- **Outcome:** Approved for Phase 2 classification
