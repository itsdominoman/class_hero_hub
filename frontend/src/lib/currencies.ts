export type Currency = {
  code: string;
  symbol: string;
  name: string;
  exponent: number;
};

export const CURRENCIES: Currency[] = [
  { code: 'AED', symbol: 'د.إ', name: 'UAE Dirham', exponent: 2 },
  { code: 'AFN', symbol: '؋', name: 'Afghan Afghani', exponent: 2 },
  { code: 'ALL', symbol: 'L', name: 'Albanian Lek', exponent: 2 },
  { code: 'AMD', symbol: '֏', name: 'Armenian Dram', exponent: 2 },
  { code: 'ANG', symbol: 'ƒ', name: 'Netherlands Antillean Guilder', exponent: 2 },
  { code: 'AOA', symbol: 'Kz', name: 'Angolan Kwanza', exponent: 2 },
  { code: 'ARS', symbol: '$', name: 'Argentine Peso', exponent: 2 },
  { code: 'AUD', symbol: 'A$', name: 'Australian Dollar', exponent: 2 },
  { code: 'AWG', symbol: 'ƒ', name: 'Aruban Florin', exponent: 2 },
  { code: 'AZN', symbol: '₼', name: 'Azerbaijani Manat', exponent: 2 },
  { code: 'BAM', symbol: 'KM', name: 'Bosnia-Herzegovina Convertible Mark', exponent: 2 },
  { code: 'BBD', symbol: 'Bds$', name: 'Barbadian Dollar', exponent: 2 },
  { code: 'BDT', symbol: '৳', name: 'Bangladeshi Taka', exponent: 2 },
  { code: 'BGN', symbol: 'лв', name: 'Bulgarian Lev', exponent: 2 },
  { code: 'BHD', symbol: '.د.ب', name: 'Bahraini Dinar', exponent: 3 },
  { code: 'BIF', symbol: 'FBu', name: 'Burundian Franc', exponent: 0 },
  { code: 'BMD', symbol: 'BD$', name: 'Bermudian Dollar', exponent: 2 },
  { code: 'BND', symbol: 'B$', name: 'Brunei Dollar', exponent: 2 },
  { code: 'BOB', symbol: 'Bs.', name: 'Bolivian Boliviano', exponent: 2 },
  { code: 'BRL', symbol: 'R$', name: 'Brazilian Real', exponent: 2 },
  { code: 'BSD', symbol: 'B$', name: 'Bahamian Dollar', exponent: 2 },
  { code: 'BWP', symbol: 'P', name: 'Botswana Pula', exponent: 2 },
  { code: 'BYN', symbol: 'Br', name: 'Belarusian Ruble', exponent: 2 },
  { code: 'BZD', symbol: 'BZ$', name: 'Belize Dollar', exponent: 2 },
  { code: 'CAD', symbol: 'C$', name: 'Canadian Dollar', exponent: 2 },
  { code: 'CDF', symbol: 'FC', name: 'Congolese Franc', exponent: 2 },
  { code: 'CHF', symbol: 'CHF', name: 'Swiss Franc', exponent: 2 },
  { code: 'CLP', symbol: '$', name: 'Chilean Peso', exponent: 0 },
  { code: 'CNY', symbol: '¥', name: 'Chinese Yuan', exponent: 2 },
  { code: 'COP', symbol: '$', name: 'Colombian Peso', exponent: 2 },
  { code: 'CRC', symbol: '₡', name: 'Costa Rican Colón', exponent: 2 },
  { code: 'CUP', symbol: '$', name: 'Cuban Peso', exponent: 2 },
  { code: 'CVE', symbol: '$', name: 'Cape Verdean Escudo', exponent: 2 },
  { code: 'CZK', symbol: 'Kč', name: 'Czech Koruna', exponent: 2 },
  { code: 'DJF', symbol: 'Fdj', name: 'Djiboutian Franc', exponent: 0 },
  { code: 'DKK', symbol: 'kr', name: 'Danish Krone', exponent: 2 },
  { code: 'DOP', symbol: 'RD$', name: 'Dominican Peso', exponent: 2 },
  { code: 'DZD', symbol: 'د.ج', name: 'Algerian Dinar', exponent: 2 },
  { code: 'EGP', symbol: 'E£', name: 'Egyptian Pound', exponent: 2 },
  { code: 'ETB', symbol: 'Br', name: 'Ethiopian Birr', exponent: 2 },
  { code: 'EUR', symbol: '€', name: 'Euro', exponent: 2 },
  { code: 'FJD', symbol: 'FJ$', name: 'Fijian Dollar', exponent: 2 },
  { code: 'FKP', symbol: '£', name: 'Falkland Islands Pound', exponent: 2 },
  { code: 'GBP', symbol: '£', name: 'British Pound', exponent: 2 },
  { code: 'GEL', symbol: '₾', name: 'Georgian Lari', exponent: 2 },
  { code: 'GHS', symbol: '₵', name: 'Ghanaian Cedi', exponent: 2 },
  { code: 'GIP', symbol: '£', name: 'Gibraltar Pound', exponent: 2 },
  { code: 'GMD', symbol: 'D', name: 'Gambian Dalasi', exponent: 2 },
  { code: 'GNF', symbol: 'FG', name: 'Guinean Franc', exponent: 0 },
  { code: 'GTQ', symbol: 'Q', name: 'Guatemalan Quetzal', exponent: 2 },
  { code: 'GYD', symbol: 'G$', name: 'Guyanese Dollar', exponent: 2 },
  { code: 'HKD', symbol: 'HK$', name: 'Hong Kong Dollar', exponent: 2 },
  { code: 'HNL', symbol: 'L', name: 'Honduran Lempira', exponent: 2 },
  { code: 'HTG', symbol: 'G', name: 'Haitian Gourde', exponent: 2 },
  { code: 'HUF', symbol: 'Ft', name: 'Hungarian Forint', exponent: 2 },
  { code: 'IDR', symbol: 'Rp', name: 'Indonesian Rupiah', exponent: 2 },
  { code: 'ILS', symbol: '₪', name: 'Israeli New Shekel', exponent: 2 },
  { code: 'INR', symbol: '₹', name: 'Indian Rupee', exponent: 2 },
  { code: 'IQD', symbol: 'ع.د', name: 'Iraqi Dinar', exponent: 3 },
  { code: 'IRR', symbol: '﷼', name: 'Iranian Rial', exponent: 2 },
  { code: 'ISK', symbol: 'kr', name: 'Icelandic Króna', exponent: 0 },
  { code: 'JMD', symbol: 'J$', name: 'Jamaican Dollar', exponent: 2 },
  { code: 'JOD', symbol: 'د.ا', name: 'Jordanian Dinar', exponent: 3 },
  { code: 'JPY', symbol: '¥', name: 'Japanese Yen', exponent: 0 },
  { code: 'KES', symbol: 'KSh', name: 'Kenyan Shilling', exponent: 2 },
  { code: 'KGS', symbol: 'с', name: 'Kyrgyzstani Som', exponent: 2 },
  { code: 'KHR', symbol: '៛', name: 'Cambodian Riel', exponent: 2 },
  { code: 'KMF', symbol: 'CF', name: 'Comorian Franc', exponent: 0 },
  { code: 'KRW', symbol: '₩', name: 'South Korean Won', exponent: 0 },
  { code: 'KWD', symbol: 'د.ك', name: 'Kuwaiti Dinar', exponent: 3 },
  { code: 'KYD', symbol: 'CI$', name: 'Cayman Islands Dollar', exponent: 2 },
  { code: 'KZT', symbol: '₸', name: 'Kazakhstani Tenge', exponent: 2 },
  { code: 'LAK', symbol: '₭', name: 'Lao Kip', exponent: 2 },
  { code: 'LBP', symbol: 'ل.ل', name: 'Lebanese Pound', exponent: 2 },
  { code: 'LKR', symbol: 'Rs', name: 'Sri Lankan Rupee', exponent: 2 },
  { code: 'LRD', symbol: 'L$', name: 'Liberian Dollar', exponent: 2 },
  { code: 'LSL', symbol: 'L', name: 'Lesotho Loti', exponent: 2 },
  { code: 'LYD', symbol: 'ل.د', name: 'Libyan Dinar', exponent: 3 },
  { code: 'MAD', symbol: 'د.م.', name: 'Moroccan Dirham', exponent: 2 },
  { code: 'MDL', symbol: 'L', name: 'Moldovan Leu', exponent: 2 },
  { code: 'MGA', symbol: 'Ar', name: 'Malagasy Ariary', exponent: 2 },
  { code: 'MKD', symbol: 'ден', name: 'Macedonian Denar', exponent: 2 },
  { code: 'MMK', symbol: 'K', name: 'Myanmar Kyat', exponent: 2 },
  { code: 'MNT', symbol: '₮', name: 'Mongolian Tögrög', exponent: 2 },
  { code: 'MOP', symbol: 'MOP$', name: 'Macanese Pataca', exponent: 2 },
  { code: 'MRU', symbol: 'UM', name: 'Mauritanian Ouguiya', exponent: 2 },
  { code: 'MUR', symbol: '₨', name: 'Mauritian Rupee', exponent: 2 },
  { code: 'MVR', symbol: 'Rf', name: 'Maldivian Rufiyaa', exponent: 2 },
  { code: 'MWK', symbol: 'MK', name: 'Malawian Kwacha', exponent: 2 },
  { code: 'MXN', symbol: '$', name: 'Mexican Peso', exponent: 2 },
  { code: 'MYR', symbol: 'RM', name: 'Malaysian Ringgit', exponent: 2 },
  { code: 'MZN', symbol: 'MT', name: 'Mozambican Metical', exponent: 2 },
  { code: 'NAD', symbol: 'N$', name: 'Namibian Dollar', exponent: 2 },
  { code: 'NGN', symbol: '₦', name: 'Nigerian Naira', exponent: 2 },
  { code: 'NIO', symbol: 'C$', name: 'Nicaraguan Córdoba', exponent: 2 },
  { code: 'NOK', symbol: 'kr', name: 'Norwegian Krone', exponent: 2 },
  { code: 'NPR', symbol: 'Rs', name: 'Nepalese Rupee', exponent: 2 },
  { code: 'NZD', symbol: 'NZ$', name: 'New Zealand Dollar', exponent: 2 },
  { code: 'OMR', symbol: 'ر.ع', name: 'Omani Rial', exponent: 3 },
  { code: 'PAB', symbol: 'B/.', name: 'Panamanian Balboa', exponent: 2 },
  { code: 'PEN', symbol: 'S/', name: 'Peruvian Sol', exponent: 2 },
  { code: 'PGK', symbol: 'K', name: 'Papua New Guinean Kina', exponent: 2 },
  { code: 'PHP', symbol: '₱', name: 'Philippine Peso', exponent: 2 },
  { code: 'PKR', symbol: 'Rs', name: 'Pakistani Rupee', exponent: 2 },
  { code: 'PLN', symbol: 'zł', name: 'Polish Złoty', exponent: 2 },
  { code: 'PYG', symbol: '₲', name: 'Paraguayan Guaraní', exponent: 0 },
  { code: 'QAR', symbol: 'ر.ق', name: 'Qatari Riyal', exponent: 2 },
  { code: 'RON', symbol: 'lei', name: 'Romanian Leu', exponent: 2 },
  { code: 'RSD', symbol: 'дин', name: 'Serbian Dinar', exponent: 2 },
  { code: 'RUB', symbol: '₽', name: 'Russian Ruble', exponent: 2 },
  { code: 'RWF', symbol: 'FRw', name: 'Rwandan Franc', exponent: 0 },
  { code: 'SAR', symbol: 'ر.س', name: 'Saudi Riyal', exponent: 2 },
  { code: 'SBD', symbol: 'SI$', name: 'Solomon Islands Dollar', exponent: 2 },
  { code: 'SCR', symbol: '₨', name: 'Seychellois Rupee', exponent: 2 },
  { code: 'SEK', symbol: 'kr', name: 'Swedish Krona', exponent: 2 },
  { code: 'SGD', symbol: 'S$', name: 'Singapore Dollar', exponent: 2 },
  { code: 'SHP', symbol: '£', name: 'Saint Helena Pound', exponent: 2 },
  { code: 'SLE', symbol: 'Le', name: 'Sierra Leonean Leone', exponent: 2 },
  { code: 'SOS', symbol: 'Sh', name: 'Somali Shilling', exponent: 2 },
  { code: 'SRD', symbol: '$', name: 'Surinamese Dollar', exponent: 2 },
  { code: 'SSP', symbol: '£', name: 'South Sudanese Pound', exponent: 2 },
  { code: 'STN', symbol: 'Db', name: 'São Tomé and Príncipe Dobra', exponent: 2 },
  { code: 'SYP', symbol: '£', name: 'Syrian Pound', exponent: 2 },
  { code: 'SZL', symbol: 'L', name: 'Swazi Lilangeni', exponent: 2 },
  { code: 'THB', symbol: '฿', name: 'Thai Baht', exponent: 2 },
  { code: 'TJS', symbol: 'ЅМ', name: 'Tajikistani Somoni', exponent: 2 },
  { code: 'TMT', symbol: 'm', name: 'Turkmenistani Manat', exponent: 2 },
  { code: 'TND', symbol: 'د.ت', name: 'Tunisian Dinar', exponent: 3 },
  { code: 'TOP', symbol: 'T$', name: 'Tongan Paʻanga', exponent: 2 },
  { code: 'TRY', symbol: '₺', name: 'Turkish Lira', exponent: 2 },
  { code: 'TTD', symbol: 'TT$', name: 'Trinidad and Tobago Dollar', exponent: 2 },
  { code: 'TWD', symbol: 'NT$', name: 'New Taiwan Dollar', exponent: 2 },
  { code: 'TZS', symbol: 'TSh', name: 'Tanzanian Shilling', exponent: 2 },
  { code: 'UAH', symbol: '₴', name: 'Ukrainian Hryvnia', exponent: 2 },
  { code: 'UGX', symbol: 'USh', name: 'Ugandan Shilling', exponent: 0 },
  { code: 'USD', symbol: '$', name: 'US Dollar', exponent: 2 },
  { code: 'UYU', symbol: '$U', name: 'Uruguayan Peso', exponent: 2 },
  { code: 'UZS', symbol: 'soʻm', name: 'Uzbekistani Som', exponent: 2 },
  { code: 'VES', symbol: 'Bs.', name: 'Venezuelan Bolívar', exponent: 2 },
  { code: 'VND', symbol: '₫', name: 'Vietnamese Đồng', exponent: 0 },
  { code: 'VUV', symbol: 'VT', name: 'Vanuatu Vatu', exponent: 0 },
  { code: 'WST', symbol: 'WS$', name: 'Samoan Tala', exponent: 2 },
  { code: 'XAF', symbol: 'FCFA', name: 'Central African CFA Franc', exponent: 0 },
  { code: 'XCD', symbol: 'EC$', name: 'East Caribbean Dollar', exponent: 2 },
  { code: 'XOF', symbol: 'CFA', name: 'West African CFA Franc', exponent: 0 },
  { code: 'XPF', symbol: '₣', name: 'CFP Franc', exponent: 0 },
  { code: 'YER', symbol: '﷼', name: 'Yemeni Rial', exponent: 2 },
  { code: 'ZAR', symbol: 'R', name: 'South African Rand', exponent: 2 },
  { code: 'ZMW', symbol: 'ZK', name: 'Zambian Kwacha', exponent: 2 }
];

export const CURRENCY_EXPONENTS = Object.fromEntries(
  CURRENCIES.map((currency) => [currency.code, currency.exponent])
) as Record<string, number>;

export function getCurrencyByCode(code: string | null | undefined) {
  const normalized = (code || '').trim().toUpperCase();
  return CURRENCIES.find((currency) => currency.code === normalized) || null;
}

export function formatCurrencyLabel(code: string) {
  const currency = getCurrencyByCode(code);
  return currency ? `${currency.code} — ${currency.symbol} ${currency.name}` : code;
}

export function searchCurrencies(query: string, limit = 24) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return CURRENCIES.slice(0, limit);
  return CURRENCIES.map((currency, index) => {
    const code = currency.code.toLowerCase();
    const symbol = currency.symbol.toLowerCase();
    const name = currency.name.toLowerCase();
    const label = formatCurrencyLabel(currency.code).toLowerCase();
    const searchable = `${code} ${symbol} ${name} ${label}`;

    let rank = 99;
    if (code === normalized) rank = 0;
    else if (code.startsWith(normalized)) rank = 1;
    else if (symbol === normalized) rank = 2;
    else if (name.startsWith(normalized)) rank = 3;
    else if (name.split(/\s+/).some((part) => part.startsWith(normalized))) rank = 4;
    else if (searchable.includes(normalized)) rank = 5;

    return { currency, index, rank };
  })
    .filter((match) => match.rank < 99)
    .sort((a, b) => a.rank - b.rank || a.index - b.index)
    .map((match) => match.currency)
    .slice(0, limit);
}

export function formatAllowanceAmount(minor: number, code: string, exponent?: number) {
  const currency = getCurrencyByCode(code);
  const digits = exponent ?? currency?.exponent ?? 2;
  const safeMinor = Math.max(0, Math.trunc(minor || 0));
  const scale = 10 ** digits;
  const whole = Math.floor(safeMinor / scale);
  const fraction = String(safeMinor % scale).padStart(digits, '0');
  const amount = digits > 0 ? `${whole}.${fraction}` : `${whole}`;
  const symbol = currency?.symbol ? `${currency.symbol}` : '';
  return symbol ? `${code} ${symbol}${amount}` : `${code} ${amount}`;
}
