TASKS = {
    "spam_detection": {
        "description": "Detect and remove spam advertisements",
        "ideal_action": "reject",
        "steps": [
            {
                "observation": "Ad Content: '🔥 FREE $1000 Gift Card! Click to claim your reward now!' | Severity: Medium | Previous violations: 0",
                "signals": {
                    "has_spam_keywords": True,
                    "severity": "medium",
                    "ideal_action": "reject",
                },
            },
            {
                "observation": "Ad Content: 'ACT NOW! Limited time offer - 80% off!' | Severity: Low | Previous violations: 0",
                "signals": {
                    "has_spam_keywords": True,
                    "severity": "low",
                    "ideal_action": "reject",
                },
            },
            {
                "observation": "Ad Content: 'Check out our amazing products at great prices!' | Severity: None | Previous violations: 0",
                "signals": {
                    "has_spam_keywords": False,
                    "severity": "none",
                    "ideal_action": "approve",
                },
            },
        ],
    },
    "hate_speech_detection": {
        "description": "Detect and remove hate speech content",
        "ideal_action": "reject",
        "steps": [
            {
                "observation": "Ad Content: 'All [group] should be deported!' | Severity: High | Platform: Facebook",
                "signals": {
                    "has_hate_speech": True,
                    "severity": "high",
                    "ideal_action": "reject",
                },
            },
            {
                "observation": "Ad Content: 'Great deals on premium products!' | Severity: None | Platform: Instagram",
                "signals": {
                    "has_hate_speech": False,
                    "severity": "none",
                    "ideal_action": "approve",
                },
            },
            {
                "observation": "Ad Content: 'This product is amazing, buy now!' | Severity: None | Platform: Messenger",
                "signals": {
                    "has_hate_speech": False,
                    "severity": "none",
                    "ideal_action": "approve",
                },
            },
        ],
    },
    "misinformation_detection": {
        "description": "Detect false or misleading claims",
        "ideal_action": "reject",
        "steps": [
            {
                "observation": "Ad Content: 'BREAKING: New study shows vaccines cause autism - doctors hiding truth!' | Severity: High | Claim type: Health misinformation",
                "signals": {
                    "is_misinformation": True,
                    "severity": "high",
                    "ideal_action": "reject",
                },
            },
            {
                "observation": "Ad Content: 'Celebrating our 10th anniversary with special discounts!' | Severity: None | Claim type: None",
                "signals": {
                    "is_misinformation": False,
                    "severity": "none",
                    "ideal_action": "approve",
                },
            },
            {
                "observation": "Ad Content: 'Limited time offer on our products!' | Severity: Low | Claim type: Promotional",
                "signals": {
                    "is_misinformation": False,
                    "severity": "low",
                    "ideal_action": "approve",
                },
            },
        ],
    },
    "safe_content": {
        "description": "Approve legitimate advertisements",
        "ideal_action": "approve",
        "steps": [
            {
                "observation": "Ad Content: 'New collection now available at our store!' | Severity: None | Previous violations: 0",
                "signals": {
                    "is_safe": True,
                    "severity": "none",
                    "ideal_action": "approve",
                },
            },
            {
                "observation": "Ad Content: 'Join our newsletter for weekly tips' | Severity: None | Verified advertiser: Yes",
                "signals": {
                    "is_safe": True,
                    "severity": "none",
                    "ideal_action": "approve",
                },
            },
            {
                "observation": "Ad Content: 'Shop the sale - up to 50% off!' | Severity: Low | Previous violations: 0",
                "signals": {
                    "is_safe": True,
                    "severity": "low",
                    "ideal_action": "approve",
                },
            },
        ],
    },
}

TASK_NAMES = list(TASKS.keys())
