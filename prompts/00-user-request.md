[← Return to Module VII — Assignment 4: Live Market Workstation](https://psu.instructure.com/courses/2484533/modules#context_module_6139771)
Individual · four equal-weight parts: three Canvas submissions and one live in-class presentation

Assignment 4 contributes 25% of the course grade.
Assignment 4 brings together the skills developed through the calculator, the simulated Expedia replica, and the mental health support bot. Students will build one local AI-assisted market workstation and trading bot, continuing the course practice of directing a coding agent, inspecting generated code, testing the running application, and explaining design decisions.

A market workstation helps a person follow changing prices, interpret patterns, and examine the consequences of a trading decision. A candlestick chart summarizes each time interval through its opening, highest, lowest, and closing prices; corresponding volume shows how much was traded. Indicators add derived information, while a simulated account makes the consequences of decisions visible.

The completed application connects observation, interpretation, action, and review. Its dashboard shows the market, its indicators provide a basis for decisions, and its trading simulation records the results. AI contributes decision support, chart-image interpretation, and conversation through text and live audio. Students must be able to explain how these capabilities work together and what their evidence establishes.
The central problem is to turn a changing, noisy stream of market observations into an understandable interface and an accountable decision-making process. The assignment has five connected concerns:
- Visualize domain-specific data. Use a charting library to present price and volume clearly and keep the dashboard understandable as new observations arrive.
- Coordinate live services and stored data. Connect multiple APIs, use WebSockets for real-time communication, and preserve useful records in a backend database.
- Create intelligence from data. Derive indicators and signals from price observations so that market behavior can be interpreted. This concerns calculated information, such as moving averages and crossovers; chart-image interpretation by a model has a separate role.
- Support AI-assisted decisions and automation. Provide relevant context to a model, check its response, and connect the resulting decision to a simulated trading bot. Text and audio interaction should help the user understand the application’s observations and actions.
- Account for simulated outcomes. Track trades, account state, and profit or loss, and use historical backtesting to examine how a strategy behaves over time.
The three implementation parts develop these concerns cumulatively. Students choose the interface and implementation within the requirements below; the evidence should make each connection understandable and verifiable.
Reference application. Explore [TradingViewLinks to an external site.](https://www.tradingview.com/chart/) as a reference for the workstation’s interface. Consider how it presents candlestick charts, volume, indicators, and market information, and which design choices would help make the student application understandable and usable.

Charting libraries. TradingView’s [Lightweight ChartsLinks to an external site.](https://github.com/tradingview/lightweight-charts) is one open-source option for financial charts in the browser. Students may choose another suitable library and should explain how it supports their dashboard.

Technical indicators. Indicators derive information from market observations. This assignment uses two simple moving averages and their crossover as the required starting strategy. Correct calculation and clear interpretation matter; an indicator is not a guarantee of a profitable decision.

The relevant definitions are:
- SMA (simple moving average). The arithmetic mean of the closing price over the last N bars, recomputed on each new bar. An SMA(20) on 5-minute candles is the average close of the last twenty five-minute bars.
- EMA (exponential moving average; optional). An average that assigns greater weight to recent prices. An implementation should document its formula and how the first value is initialized.
- SMA crossover. Calculate two simple moving averages over different window lengths. A crossover occurs when the shorter-window SMA moves from one side of the longer-window SMA to the other. A strategy can interpret an upward crossover as a buy signal and a downward crossover as a sell signal. For this project, show and explain how the crossover contributes to the simulated trading bot’s decisions.
- RSI measures the size of recent gains against recent losses on a 0–100 scale; MACD is built from the difference between two EMAs. Both are optional here and both are well documented.
A signal based on an unfinished candle can change as the price moves. The application must distinguish a provisional signal from one based on a completed candle.

Backtesting and its characteristic failures. Backtesting simulates a strategy on historical data. It differs from replaying recorded observations: a backtest also evaluates the strategy’s simulated decisions and outcomes. When evaluating a strategy, three common failure modes should be understood:
- Look-ahead bias — the strategy is evaluated using information that would not have been available at the moment of decision.
- Survivorship bias — the test universe includes only instruments that still exist.
- Overfitting — parameters are tuned until the strategy explains the historical sample precisely and generalizes poorly.
These problems can make a strategy appear more effective than the evidence supports. A historical result does not establish future performance.

Event-driven versus vectorized architectures. Two established structures are to process observations sequentially or compute across arrays. Either approach must restrict each decision to information available at that moment.

Existing platforms. Backtrader and QuantConnect provide examples of separating strategy logic from data processing. They are optional references; neither platform is required for this project.
Use the familiar Vue frontend, FastAPI backend, and SQLite database on localhost. Market-data, model, and live-audio services have distinct roles; students should explain what information each receives, what it returns, and how it connects to the rest of the application. Deployment and a mobile build are not required.

Yahoo Finance. Use Yahoo Finance for the live-streaming market-data portion of the project. The [yfinance packageLinks to an external site.](https://pypi.org/project/yfinance/) and its [documentationLinks to an external site.](https://ranaroussi.github.io/yfinance/) are a starting point. The package is an independent tool, not an official Yahoo library; its [WebSocket documentationLinks to an external site.](https://ranaroussi.github.io/yfinance/reference/yfinance.websocket.html) describes streaming price updates. Check the actual availability and timing of the chosen data and show its age in the application. A frequently refreshed display does not by itself establish that source data is current.

Other sources. Students may examine [FinnhubLinks to an external site.](https://finnhub.io/docs/api) or another source for comparison. The required live connection remains Yahoo Finance. Students should document the availability and limitations of their chosen data.

Market hours. The chosen instrument may not trade when development or a demonstration takes place. Recorded observations allow the application to be exercised when live updates are unavailable.

Bar formation. A candle for the current interval is incomplete until that interval ends. Its high, low, and close continue to change. Any calculation consuming the current bar is consuming a value that has not settled.
Parts 4.1–4.3 are cumulative submissions of the same application. Part 4.4 is its live in-class presentation. Students choose the charting library, interface, market instruments, SMA window lengths, and AI services, and explain those choices. Continue the browser-testing, Git/GitHub, documentation, and AI-use evidence practices established in the course.
Outcome: a working client-server dashboard with live-streaming market data and persistent records.
- Live visualization. Connect to Yahoo Finance and use a charting library to display updating candlesticks and corresponding volume. Use WebSockets for real-time communication. Make the data source, age, and feed status visible.
- Persistence and replay. Store market observations in SQLite so that they can be retrieved and replayed. Preserve observation identity, source and receipt times, revisions, and whether a candle is complete. Explain and test how duplicate, revised, and out-of-order observations are handled.
- Working evidence. Demonstrate the path from the live source through the backend to the chart and database, including an unavailable-feed condition. Maintain the README, agent instructions, and design notes describing the data flow and SQLite schema. Document database initialization and startup without exposing credentials.
CSV loading is ungraded in-class practice. The Part 4.1 deliverable must demonstrate live streaming. Recorded observations support development and replay when the market is closed.