import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import type { RubricScore } from "@/lib/types/certification";

const CATEGORIES: {
  key: keyof Pick<
    RubricScore,
    | "subject_knowledge"
    | "instructional_quality"
    | "pedagogical_adaptability"
    | "organization"
  >;
  rationaleKey: keyof RubricScore;
  label: string;
  max: number;
}[] = [
  {
    key: "subject_knowledge",
    rationaleKey: "subject_knowledge_rationale",
    label: "Subject knowledge",
    max: 20,
  },
  {
    key: "instructional_quality",
    rationaleKey: "instructional_quality_rationale",
    label: "Instructional quality",
    max: 40,
  },
  {
    key: "pedagogical_adaptability",
    rationaleKey: "pedagogical_adaptability_rationale",
    label: "Pedagogical adaptability",
    max: 20,
  },
  {
    key: "organization",
    rationaleKey: "organization_rationale",
    label: "Organization",
    max: 20,
  },
];

export function RubricScoreCard({ score }: { score: RubricScore }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div className="flex items-baseline gap-2">
          <CardTitle className="font-heading text-3xl font-semibold">
            {score.total_score}
          </CardTitle>
          <span className="text-sm text-muted-foreground">/ 100</span>
        </div>
        <Badge variant={score.passed ? "default" : "destructive"}>
          {score.passed ? "Passed" : "Not yet passed"}
        </Badge>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {CATEGORIES.map((category, index) => {
          const value = score[category.key] as number;
          return (
            <div key={category.key}>
              {index > 0 && <Separator className="mb-4" />}
              <div className="flex items-baseline justify-between">
                <span className="text-sm font-medium">{category.label}</span>
                <span className="text-sm text-muted-foreground tabular-nums">
                  {value} / {category.max}
                </span>
              </div>
              <Progress value={value} max={category.max} className="mt-2" />
              <p className="mt-2 text-sm text-muted-foreground">
                {score[category.rationaleKey] as string}
              </p>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
