import * as React from 'react';
import Button from '@mui/material/Button';
import DiscordIcon from './DiscordIcon';
import logo from "./logo.png";
import "./App.css";
import { ThemeProvider } from '@mui/material/styles';
import { theme as DiscordTheme } from './DiscordTheme';

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <img src={logo} className="App-logo" alt="logo" />
        <p> Authenticate below to export your mnemonic. </p>
        <ThemeProvider theme={DiscordTheme}>
          <Button href="/auth/discord" variant="contained" color="blurple" sx={{ height: 1/2 }} startIcon={<DiscordIcon />}>
            Authenticate with Discord
          </Button>
        </ThemeProvider>
      </header>
    </div>
  );
}

export default App;
