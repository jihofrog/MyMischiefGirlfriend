using UnityEngine;
using UnityEngine.Animations;
using UnityEngine.Playables;

namespace MMG.Experiments.EyeView
{
    /// <summary>
    /// test only: a PlayableAsset for PlayableDirector without the Timeline package: plays one clip (looping) into the
    /// Animator of the director's GameObject, evaluated by the Director like a Timeline animation track.
    /// </summary>
    [CreateAssetMenu(menuName = "MMG Experiments/EyeView Director Asset")]
    public sealed class EyeViewDirectorAsset : PlayableAsset
    {
        public AnimationClip clip;

        public override Playable CreatePlayable(PlayableGraph graph, GameObject owner)
        {
            var animator = owner.GetComponent<Animator>();
            var p = AnimationClipPlayable.Create(graph, clip);
            p.SetApplyFootIK(false);
            var output = AnimationPlayableOutput.Create(graph, "EyeViewDirector", animator);
            output.SetSourcePlayable(p);
            return p;
        }

        public override double duration => clip != null ? clip.length : 1.0;
    }
}
