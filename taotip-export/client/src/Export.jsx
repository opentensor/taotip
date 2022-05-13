import React from "react";
import Button from "@mui/material/Button";
import DownloadIcon from "@mui/icons-material/Download";
import FormControl from "@mui/material/FormControl";
import TextField from "@mui/material/TextField";
import InputLabel from "@mui/material/InputLabel";
import FormHelperText from "@mui/material/FormHelperText";
import axios from "axios";
import "./Export.css";

function Export() {
  const [password, setPassword] = React.useState("");
  const [error, setError] = React.useState(false);
  const [errorText, setErrorText] = React.useState("");

  const handlePasswordChange = (event) => {
    setPassword(event.target.value);
  };

  const handleExport = async () => {
        setError(false);
        try {
            const response = await axios.post(
                "/api/export",
                {
                    password: password,
                }
            );
            // Download the file from json
            if (response.status === 200) {
                const address = response.data.address;
                const file = new Blob([JSON.stringify(response.data)], { type: "application/json" });
                const fileURL = URL.createObjectURL(file);
                const link = document.createElement("a");
                link.href = fileURL;
                link.setAttribute("download", `${address}-taotip-export.json`);
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);       
            }
        } catch (error) {
            setError(true);            
            setErrorText("Unknown Error");
            if (error.response) {
                
                if (error.response?.status === 404) {
                    // User not found in the database
                    
                    setErrorText("No address for this user");
                } else {
                    console.error(`status: ${error.response.status}; ${error.response.data.error}`);
                }
            } else {
                console.error("Error", error);
            }
        }
    };

  return (
    <div className="Export">
      <div className="Export-root">
        <p> You're authenticated! Download your wallet export below. </p>
        <div className="Export-form">
          <FormControl>
            <TextField
              id="password"
              type="password"
              label="Export Password"
              required
              variant="filled"
              value={password}
              onChange={handlePasswordChange}
              error={error}
              helperText={error ? errorText :
                  "This password will be used to encrypt your wallet for safe export."}
            />
            <Button
              href="#"
              variant="contained"
              color="primary"
              sx={{ height: 1 / 2 }}
              startIcon={<DownloadIcon />}
              onClick={handleExport}
            >
              Export Wallet as JSON
            </Button>
          </FormControl>
        </div>
      </div>
    </div>
  );
}

export default Export;
