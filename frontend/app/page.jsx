import { MissionControl } from '@/components/mission-control/mission-control'
import { getConjunctions, getMissionStatus, getOrbitalScenario } from '@/lib/data-source'

// Server component: loads the data, then hands it to the interactive client UI.
export default async function Page() {
  const scenario = await getOrbitalScenario()
  const status = await getMissionStatus()
  const conjunctions = await getConjunctions(scenario, status)

  return <MissionControl scenario={scenario} status={status} conjunctions={conjunctions} />
}
