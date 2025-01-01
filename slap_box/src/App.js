import { servers, versions, auth, tokenEnabled} from './api';

if (tokenEnabled === false) {
  auth.login({ username: "GG", password: "GG" }).then((response) => {
    localStorage.setItem("token", response.data.token);
  }).catch((error) => console.error("Login failed", error));
}

versions.getAll().catch((error) => {
  if (error.response.status === 422) {
    console.error("Unprocessable Entity: Check the token or request data");
  } else {
    console.error("Error:", error);
  }
});

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <p>
          Edit <code>src/App.js</code> and save to reload.
        </p>
        <a
          className="App-link"
          href="https://reactjs.org"
          target="_blank"
          rel="noopener noreferrer"
        >
        </a>
      </header>
    </div>
  );
}

export default App;
