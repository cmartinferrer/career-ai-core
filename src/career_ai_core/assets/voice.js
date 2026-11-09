(() => {
    let latestText = "";
    let latestMessageKey = "";
    let activeUtterance = null;
    let autoEnabled = true;

    function extractText(content) {
        if (typeof content === "string") {
            return content;
        }

        if (Array.isArray(content)) {
            return content
                .filter(item => item?.type === "text")
                .map(item => item.text || "")
                .join("\n");
        }

        return "";
    }

    function cleanText(text) {
        return text
            .replace(/```[\s\S]*?```/g, " ")
            .replace(/`([^`]+)`/g, "$1")
            .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
            .replace(/[*#_~>|]/g, " ")
            .replace(/\s+/g, " ")
            .trim();
    }

    function detectLanguage(text) {
        const spanish = (
            text.match(
                /\b(el|la|los|las|que|para|con|una|tiene|trabajó|experiencia|proyecto)\b/gi
            ) || []
        ).length;

        const english = (
            text.match(
                /\b(the|and|with|has|worked|experience|project|development|his|for)\b/gi
            ) || []
        ).length;

        return english > spanish ? "en-US" : "es-ES";
    }

    function speak(text) {
        if (!("speechSynthesis" in window)) {
            return;
        }

        const cleaned = cleanText(text);

        if (!cleaned) {
            return;
        }

        window.speechSynthesis.cancel();

        const utterance = new SpeechSynthesisUtterance(cleaned);
        utterance.lang = detectLanguage(cleaned);
        utterance.rate = 1;
        utterance.pitch = 1;

        const voices = window.speechSynthesis.getVoices();
        const language = utterance.lang.split("-")[0];

        const matchingVoice = voices.find(
            voice => voice.lang.toLowerCase() === utterance.lang.toLowerCase()
        ) || voices.find(
            voice => voice.lang.toLowerCase().startsWith(language)
        );

        if (matchingVoice) {
            utterance.voice = matchingVoice;
        }

        activeUtterance = utterance;

        utterance.onend = () => {
            if (activeUtterance === utterance) {
                activeUtterance = null;
            }
        };

        utterance.onerror = () => {
            if (activeUtterance === utterance) {
                activeUtterance = null;
            }
        };

        window.speechSynthesis.speak(utterance);
    }

    window.cmfVoice = {
        onMessagesChanged(messages) {
            if (!Array.isArray(messages) || !messages.length) {
                return;
            }

            const last = messages[messages.length - 1];

            if (last?.role !== "assistant") {
                return;
            }

            const text = extractText(last.content);

            if (!text.trim()) {
                return;
            }

            const key = `${messages.length}:${text}`;

            if (key === latestMessageKey) {
                return;
            }

            latestMessageKey = key;
            latestText = text;

            if (autoEnabled) {
                speak(text);
            }
        },

        toggleAuto() {
            autoEnabled = !autoEnabled;
            return autoEnabled;
        },

        replay() {
            if (latestText) {
                speak(latestText);
            }
        },

        stop() {
            window.speechSynthesis?.cancel();
            activeUtterance = null;
        }
    };
})();
