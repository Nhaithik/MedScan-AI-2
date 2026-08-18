/* MediScan AI — shared dark mode + language engine.
   Included on every page so preferences persist (via localStorage)
   as the user navigates between pages. */

(function () {
  const DARK_KEY = 'mediscan_dark';
  const LANG_KEY = 'mediscan_lang';

  const LANG_NAMES = { en: 'English', hi: 'हिंदी', te: 'తెలుగు' };

  const TRANSLATIONS = {
    en: {
      brand_sub: "AI Healthcare Assistant",
      nav_dashboard: "Dashboard",
      nav_human_health: "Human Health",
      nav_animal_health: "Animal Health",
      nav_consultation_history: "Consultation History",
      nav_profile: "Profile",
      nav_settings: "Settings",
      nav_logout: "Logout",
      help_title: "Need Help?",
      help_desc: "Talk to our AI Assistant or contact a professional.",
      help_chat_btn: "Chat with AI Assistant",

      dashboard_welcome: "Welcome back, User! 👋",
      dashboard_sub: "Your AI-powered health assistant is ready to help you.",

      profile_title: "My Profile",
      profile_sub: "Manage your personal information and account settings.",
      profile_edit_btn: "Edit Profile",
      personal_info_title: "Personal Information",

      settings_title: "Settings",
      settings_sub: "Manage your account preferences and security.",
      account_settings_title: "Account Settings",
      dark_mode_label: "Dark Mode",
      dark_mode_desc: "Enable dark mode for a better viewing experience in low light.",
      language_label: "Language",
      language_desc: "Choose your preferred language.",
      change_password_title: "Change Password",
      change_password_desc: "Update your password to keep your account secure.",
      change_password_btn: "Change Password",
      delete_account_title: "Delete Account",
      delete_account_desc: "Once you delete your account, there is no going back. Please be certain.",
      delete_account_btn: "Delete Account",

      secure_note: "Your data is secure and encrypted.",

      hero_title_1: "AI-Powered",
      hero_title_2: "Health Consultation",
      hero_title_3: "for Humans & Animals",
      hero_desc: "Upload an image, describe your symptoms, and receive AI-powered preliminary health guidance using Computer Vision and Large Language Models.",
      get_started_btn: "Get Started →",
      learn_more_btn: "Learn More ▶",
      login_nav_btn: "Login",
      register_nav_btn: "Register",

      login_welcome: "Welcome Back!",
      login_sub: "Login to your account",

      signup_title: "Create Your Account",
      signup_sub: "Fill in the details below to get started",

      human_consultation_title: "Human Consultation",
      human_consultation_sub: "Provide your health details and symptoms. Our AI will analyze and provide insights.",

      animal_consultation_title: "Animal Consultation",
      animal_consultation_sub: "Provide details about your pet or animal. Our AI will analyze and provide insights.",

      history_title: "Consultation History",
      history_sub: "View and manage all your past consultations.",

      analysis_title: "AI Analysis Results",
      analysis_completed: "Analysis Completed"
    },
    hi: {
      brand_sub: "एआई हेल्थकेयर सहायक",
      nav_dashboard: "डैशबोर्ड",
      nav_human_health: "मानव स्वास्थ्य",
      nav_animal_health: "पशु स्वास्थ्य",
      nav_consultation_history: "परामर्श इतिहास",
      nav_profile: "प्रोफ़ाइल",
      nav_settings: "सेटिंग्स",
      nav_logout: "लॉगआउट",
      help_title: "मदद चाहिए?",
      help_desc: "हमारे एआई सहायक से बात करें या किसी विशेषज्ञ से संपर्क करें।",
      help_chat_btn: "एआई सहायक से चैट करें",

      dashboard_welcome: "वापसी पर स्वागत है, यूज़र! 👋",
      dashboard_sub: "आपका एआई-संचालित हेल्थ असिस्टेंट मदद के लिए तैयार है।",

      profile_title: "मेरी प्रोफ़ाइल",
      profile_sub: "अपनी व्यक्तिगत जानकारी और खाता सेटिंग्स प्रबंधित करें।",
      profile_edit_btn: "प्रोफ़ाइल संपादित करें",
      personal_info_title: "व्यक्तिगत जानकारी",

      settings_title: "सेटिंग्स",
      settings_sub: "अपनी खाता प्राथमिकताएँ और सुरक्षा प्रबंधित करें।",
      account_settings_title: "खाता सेटिंग्स",
      dark_mode_label: "डार्क मोड",
      dark_mode_desc: "कम रोशनी में बेहतर अनुभव के लिए डार्क मोड सक्षम करें।",
      language_label: "भाषा",
      language_desc: "अपनी पसंदीदा भाषा चुनें।",
      change_password_title: "पासवर्ड बदलें",
      change_password_desc: "अपने खाते को सुरक्षित रखने के लिए पासवर्ड अपडेट करें।",
      change_password_btn: "पासवर्ड बदलें",
      delete_account_title: "खाता हटाएं",
      delete_account_desc: "एक बार खाता हटाने के बाद वापसी संभव नहीं है। कृपया सुनिश्चित हों।",
      delete_account_btn: "खाता हटाएं",

      secure_note: "आपका डेटा सुरक्षित और एन्क्रिप्टेड है।",

      hero_title_1: "एआई-संचालित",
      hero_title_2: "स्वास्थ्य परामर्श",
      hero_title_3: "मनुष्यों और पशुओं के लिए",
      hero_desc: "एक तस्वीर अपलोड करें, अपने लक्षण बताएं, और कंप्यूटर विज़न व लार्ज लैंग्वेज मॉडल की मदद से एआई-आधारित प्रारंभिक स्वास्थ्य मार्गदर्शन प्राप्त करें।",
      get_started_btn: "शुरू करें →",
      learn_more_btn: "और जानें ▶",
      login_nav_btn: "लॉगिन",
      register_nav_btn: "रजिस्टर करें",

      login_welcome: "वापसी पर स्वागत है!",
      login_sub: "अपने खाते में लॉगिन करें",

      signup_title: "अपना खाता बनाएं",
      signup_sub: "शुरू करने के लिए नीचे विवरण भरें",

      human_consultation_title: "मानव परामर्श",
      human_consultation_sub: "अपने स्वास्थ्य विवरण और लक्षण बताएं। हमारा एआई विश्लेषण कर जानकारी देगा।",

      animal_consultation_title: "पशु परामर्श",
      animal_consultation_sub: "अपने पालतू या पशु के बारे में विवरण दें। हमारा एआई विश्लेषण कर जानकारी देगा।",

      history_title: "परामर्श इतिहास",
      history_sub: "अपने सभी पिछले परामर्शों को देखें और प्रबंधित करें।",

      analysis_title: "एआई विश्लेषण परिणाम",
      analysis_completed: "विश्लेषण पूर्ण हुआ"
    },
    te: {
      brand_sub: "AI హెల్త్‌కేర్ అసిస్టెంట్",
      nav_dashboard: "డాష్‌బోర్డ్",
      nav_human_health: "మానవ ఆరోగ్యం",
      nav_animal_health: "జంతు ఆరోగ్యం",
      nav_consultation_history: "సంప్రదింపుల చరిత్ర",
      nav_profile: "ప్రొఫైల్",
      nav_settings: "సెట్టింగ్‌లు",
      nav_logout: "లాగ్అవుట్",
      help_title: "సహాయం కావాలా?",
      help_desc: "మా AI అసిస్టెంట్‌తో మాట్లాడండి లేదా నిపుణుడిని సంప్రదించండి.",
      help_chat_btn: "AI అసిస్టెంట్‌తో చాట్ చేయండి",

      dashboard_welcome: "తిరిగి స్వాగతం, యూజర్! 👋",
      dashboard_sub: "మీ AI-ఆధారిత హెల్త్ అసిస్టెంట్ సహాయానికి సిద్ధంగా ఉంది.",

      profile_title: "నా ప్రొఫైల్",
      profile_sub: "మీ వ్యక్తిగత సమాచారం మరియు ఖాతా సెట్టింగ్‌లను నిర్వహించండి.",
      profile_edit_btn: "ప్రొఫైల్‌ని సవరించండి",
      personal_info_title: "వ్యక్తిగత సమాచారం",

      settings_title: "సెట్టింగ్‌లు",
      settings_sub: "మీ ఖాతా ప్రాధాన్యతలు మరియు భద్రతను నిర్వహించండి.",
      account_settings_title: "ఖాతా సెట్టింగ్‌లు",
      dark_mode_label: "డార్క్ మోడ్",
      dark_mode_desc: "తక్కువ వెలుతురులో మెరుగైన అనుభవం కోసం డార్క్ మోడ్‌ని ప్రారంభించండి.",
      language_label: "భాష",
      language_desc: "మీకు ఇష్టమైన భాషను ఎంచుకోండి.",
      change_password_title: "పాస్‌వర్డ్ మార్చండి",
      change_password_desc: "మీ ఖాతాను సురక్షితంగా ఉంచడానికి పాస్‌వర్డ్‌ను అప్‌డేట్ చేయండి.",
      change_password_btn: "పాస్‌వర్డ్ మార్చండి",
      delete_account_title: "ఖాతాను తొలగించండి",
      delete_account_desc: "మీరు ఖాతాను తొలగించిన తర్వాత తిరిగి పొందలేరు. దయచేసి నిర్ధారించుకోండి.",
      delete_account_btn: "ఖాతాను తొలగించండి",

      secure_note: "మీ డేటా సురక్షితం మరియు ఎన్‌క్రిప్ట్ చేయబడింది.",

      hero_title_1: "AI-ఆధారిత",
      hero_title_2: "ఆరోగ్య సంప్రదింపు",
      hero_title_3: "మనుషులు & జంతువుల కోసం",
      hero_desc: "ఒక చిత్రాన్ని అప్‌లోడ్ చేయండి, మీ లక్షణాలను వివరించండి, కంప్యూటర్ విజన్ మరియు లార్జ్ లాంగ్వేజ్ మోడల్స్ ఉపయోగించి AI ఆధారిత ప్రాథమిక ఆరోగ్య మార్గదర్శకత్వం పొందండి.",
      get_started_btn: "ప్రారంభించండి →",
      learn_more_btn: "మరింత తెలుసుకోండి ▶",
      login_nav_btn: "లాగిన్",
      register_nav_btn: "నమోదు చేసుకోండి",

      login_welcome: "తిరిగి స్వాగతం!",
      login_sub: "మీ ఖాతాలోకి లాగిన్ అవ్వండి",

      signup_title: "మీ ఖాతాను సృష్టించండి",
      signup_sub: "ప్రారంభించడానికి దిగువ వివరాలను పూరించండి",

      human_consultation_title: "మానవ సంప్రదింపు",
      human_consultation_sub: "మీ ఆరోగ్య వివరాలు మరియు లక్షణాలను తెలియజేయండి. మా AI విశ్లేషించి సమాచారం ఇస్తుంది.",

      animal_consultation_title: "జంతు సంప్రదింపు",
      animal_consultation_sub: "మీ పెంపుడు జంతువు గురించి వివరాలు ఇవ్వండి. మా AI విశ్లేషించి సమాచారం ఇస్తుంది.",

      history_title: "సంప్రదింపుల చరిత్ర",
      history_sub: "మీ గత సంప్రదింపులన్నింటినీ చూడండి మరియు నిర్వహించండి.",

      analysis_title: "AI విశ్లేషణ ఫలితాలు",
      analysis_completed: "విశ్లేషణ పూర్తయింది"
    }
  };

  function getStoredLang() {
    try { return localStorage.getItem(LANG_KEY) || 'en'; } catch (e) { return 'en'; }
  }
  function getStoredDark() {
    try { return localStorage.getItem(DARK_KEY) === 'true'; } catch (e) { return false; }
  }

  function applyDark(on) {
    document.body.classList.toggle('dark', on);
    document.querySelectorAll('[data-dark-toggle]').forEach(el => { el.checked = on; });
    document.querySelectorAll('[data-dark-toggle-btn]').forEach(el => {
      el.textContent = on ? '☀️' : '🌙';
    });
    try { localStorage.setItem(DARK_KEY, on ? 'true' : 'false'); } catch (e) {}
  }

  function applyTranslations(lang) {
    const dict = TRANSLATIONS[lang] || TRANSLATIONS.en;
    document.documentElement.setAttribute('lang', lang === 'en' ? 'en' : lang);
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      if (dict[key]) el.textContent = dict[key];
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      const key = el.getAttribute('data-i18n-placeholder');
      if (dict[key]) el.setAttribute('placeholder', dict[key]);
    });
    document.querySelectorAll('[data-lang-select]').forEach(el => { el.value = lang; });
    document.querySelectorAll('[data-lang-label]').forEach(el => {
      el.textContent = LANG_NAMES[lang] || LANG_NAMES.en;
    });
  }

  function setLanguage(lang) {
    if (!TRANSLATIONS[lang]) lang = 'en';
    try { localStorage.setItem(LANG_KEY, lang); } catch (e) {}
    applyTranslations(lang);
  }

  function init() {
    applyDark(getStoredDark());
    applyTranslations(getStoredLang());

    document.querySelectorAll('[data-dark-toggle]').forEach(el => {
      el.addEventListener('change', () => applyDark(el.checked));
    });
    document.querySelectorAll('[data-dark-toggle-btn]').forEach(el => {
      el.addEventListener('click', () => applyDark(!document.body.classList.contains('dark')));
    });
    document.querySelectorAll('[data-lang-select]').forEach(el => {
      el.addEventListener('change', () => setLanguage(el.value));
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Expose for any inline scripts that want to call it directly
  window.MediScanShared = { setLanguage, applyDark, getStoredDark, getStoredLang };
})();
