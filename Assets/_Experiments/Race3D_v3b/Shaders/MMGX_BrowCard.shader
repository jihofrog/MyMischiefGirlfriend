// Race3D v3b experiment: brow card over the bangs. Drawn only on hair pixels (stencil 1 from
// MMG/Experiments/ToonHairStencil), moved _Pull metres toward the camera in view space and depth tested, so only bangs
// lying close in front of the brow let it through (side hair and the far side of the head still hide it).
// _Reveal: alpha from the driver (0.8 x the strongest brow emotion).
Shader "MMG/Experiments/BrowCard"
{
    Properties
    {
        _BaseColor ("Colour", Color) = (0.306, 0.149, 0.133, 1)
        _Reveal ("Reveal", Range(0, 1)) = 0
        _Pull ("Pull toward the camera (m)", Float) = 0.03
    }
    SubShader
    {
        Tags { "RenderPipeline" = "UniversalPipeline" "RenderType" = "Transparent" "Queue" = "Transparent+10" }
        Pass
        {
            Tags { "LightMode" = "UniversalForward" }
            Blend SrcAlpha OneMinusSrcAlpha
            ZWrite Off
            ZTest LEqual
            Cull Off
            Stencil { Ref 1 Comp Equal }
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            CBUFFER_START(UnityPerMaterial)
                half4 _BaseColor; float _Reveal, _Pull;
            CBUFFER_END
            struct A { float4 positionOS : POSITION; };
            struct V { float4 positionCS : SV_POSITION; };
            V vert(A i)
            {
                V o;
                float3 vs = TransformWorldToView(TransformObjectToWorld(i.positionOS.xyz));
                vs.z += _Pull;
                o.positionCS = TransformWViewToHClip(vs);
                return o;
            }
            half4 frag(V i) : SV_Target { return half4(_BaseColor.rgb, _BaseColor.a * _Reveal); }
            ENDHLSL
        }
    }
}
