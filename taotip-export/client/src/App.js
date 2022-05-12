import logo from "./logo.svg";
import "./App.css";

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <img src={logo} className="App-logo" alt="logo" />
        <p> Login with discord to export your mnemonic. </p>
        <a
          className="App-link"
          href="/auth/discord"
          target="_blank"
          rel="noopener noreferrer"
        >
          Click to Login
        </a>
      </header>
    </div>
  );
}

export default App;
