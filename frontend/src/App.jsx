import { useState, useEffect } from 'react'

// Custom hook: encapsulates "fetch this URL, store result in state"
function useFetchData(url) {
  const [data, setData] = useState([])

  useEffect(() => {
    fetch(url)
      .then((response) => response.json())
      .then((result) => setData(result))
      .catch((error) => console.error(`Fetch failed for ${url}:`, error))
  }, [url])

  return data
}

function App() {
  const cityData = useFetchData('http://127.0.0.1:8000/stats/city-wise')
  const categoryData = useFetchData('http://127.0.0.1:8000/stats/category-wise')
  const sourceData = useFetchData('http://127.0.0.1:8000/stats/source-wise')

  return (
    <div>
      <h1>Business Listings Dashboard</h1>

      <h2>City-wise Counts</h2>
      <ul>
        {cityData.map((item) => (
          <li key={item.label}>{item.label}: {item.count}</li>
        ))}
      </ul>

      <h2>Category-wise Counts</h2>
      <ul>
        {categoryData.map((item) => (
          <li key={item.label}>{item.label}: {item.count}</li>
        ))}
      </ul>

      <h2>Source-wise Counts</h2>
      <ul>
        {sourceData.map((item) => (
          <li key={item.label}>{item.label}: {item.count}</li>
        ))}
      </ul>
    </div>
  )
}

export default App